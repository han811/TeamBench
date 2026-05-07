#!/usr/bin/env python3
"""
TeamBench cross-domain analysis.

Investigates whether team benefit in one category predicts team benefit in
another — revealing whether teamwork value is a task-structural property or
category-specific.

Steps:
  1. Load all ablation JSONs from shared/ablation_results/
  2. Per-category team uplift (mean full_score - oracle_score)
  3. Cross-category correlation matrix (per-model vectors when cross-model
     data available; per-task pairwise otherwise)
  4. Hierarchical clustering on category × metric matrix
  5. Archetype analysis: relay / open_ended / adversarial / discovery / synthesis
  6. Transfer prediction via leave-one-category-out cross-validation
  7. Outputs: JSON, LaTeX heatmap table, CSV for visualization

Usage:
    python scripts/cross_domain_analysis.py
    python scripts/cross_domain_analysis.py --ablation-dir shared/ablation_results
    python scripts/cross_domain_analysis.py --output-dir shared/paper
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.stats import pearsonr

# Allow running from repo root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from harness.paper_tables import CATEGORY_MAP, runs_to_task_metrics
from harness.compute_tni import TaskMetrics

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Canonical category short-names (deduplicated display names)
CATEGORY_DISPLAY = {
    "Security": "SEC",
    "Incident Response": "INC",
    "Code Review": "CR",
    "Specification": "SPEC",
    "Pipeline": "PIPE",
    "Integration": "INT",
    "Operations": "OPS",
    "Data Engineering": "DATA",
    "Software Eng.": "SWE",
    "Long-Horizon": "LH",
    "Policy": "POL",
    "Negotiation": "NEG",
    "Multi-language": "MULTI",
    "Testing": "TEST",
    "Information Retrieval": "IR",
    "Expertise-Asymmetry": "EA",
    "Adversarial": "TRAP",
    "Cross-System": "CROSS",
    "Distributed": "DIST",
}

# Archetype assignment: category display-name -> archetype
# Based on task structure: how knowledge flows through the team
ARCHETYPE_MAP = {
    "Security": "adversarial",       # must discover hidden vulnerabilities
    "Adversarial": "adversarial",    # spec traps, false positives
    "Cross-System": "adversarial",   # mismatched contracts
    "Incident Response": "discovery",  # root-cause investigation
    "Information Retrieval": "discovery",
    "Expertise-Asymmetry": "discovery",
    "Data Engineering": "relay",     # sequential ETL pipeline
    "Pipeline": "relay",
    "Integration": "relay",
    "Operations": "relay",
    "Software Eng.": "relay",
    "Code Review": "relay",
    "Specification": "synthesis",    # reconcile spec + implementation
    "Long-Horizon": "synthesis",
    "Multi-language": "synthesis",
    "Distributed": "synthesis",
    "Testing": "open_ended",         # many valid test strategies
    "Policy": "open_ended",
    "Negotiation": "open_ended",
}

ARCHETYPES = ["relay", "open_ended", "adversarial", "discovery", "synthesis"]

# Files to skip (not standard ablation format or known duplicates)
SKIP_FILES = {
    "crypto_dist_g3flash.log",
    "trap_cross_g3flash.log",
    "trap_cross_team_no_verify.log",
    "dynamic_runs",
    "hetero_runs",
    "ablation_runs",
    "hetero_systematic_runs",
}

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def _task_category(task_id: str) -> str:
    """Extract display category from task_id (e.g. SEC2_auth_bypass -> Security)."""
    prefix = ""
    first_part = task_id.split("_")[0] if "_" in task_id else task_id
    for ch in first_part:
        if ch.isalpha():
            prefix += ch
        else:
            break
    return CATEGORY_MAP.get(prefix.upper(), prefix.upper())


def load_all_runs(ablation_dir: str) -> dict[str, list[dict]]:
    """
    Load runs from all ablation JSONs, grouped by model name.

    Returns: {model_name: [run_dict, ...]}
    Deduplicates by (task_id, condition, seed) within each model.
    """
    dir_path = Path(ablation_dir)
    model_runs: dict[str, list[dict]] = defaultdict(list)
    seen: dict[str, set] = defaultdict(set)
    loaded_files = 0

    for fpath in sorted(dir_path.iterdir()):
        if fpath.name in SKIP_FILES or fpath.suffix != ".json":
            continue
        if fpath.is_dir():
            continue
        try:
            with open(fpath, encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue

        runs = data.get("runs", [])
        if not runs:
            continue

        # Determine model name
        model = data.get("model", fpath.stem)

        for run in runs:
            task_id = run.get("task_id", "")
            condition = run.get("condition", "")
            seed = run.get("seed", 0)
            if not task_id or not condition:
                continue
            key = (task_id, condition, seed)
            if key not in seen[model]:
                seen[model].add(key)
                model_runs[model].append(run)

        loaded_files += 1

    print(f"Loaded {loaded_files} JSON files; "
          f"{sum(len(v) for v in model_runs.values())} total runs across "
          f"{len(model_runs)} model(s)")
    return dict(model_runs)


def compute_task_uplifts(
    model_runs: dict[str, list[dict]]
) -> dict[str, dict[str, float]]:
    """
    For each model, compute per-task metrics.

    Returns: {model: {task_id: {"uplift": ..., "planning_value": ...,
                                "verification_value": ..., "oracle": ...,
                                "full": ..., "category": ...}}}
    """
    model_task_stats: dict[str, dict[str, float]] = {}

    for model, runs in model_runs.items():
        metrics_list = runs_to_task_metrics(runs)
        task_stats: dict[str, dict] = {}
        for m in metrics_list:
            pv = m.planning_value
            vv = m.verification_value
            task_stats[m.task_id] = {
                "uplift": m.team_uplift,
                "planning_value": pv if not math.isnan(pv) else 0.0,
                "verification_value": vv if not math.isnan(vv) else 0.0,
                "oracle": m.oracle_partial,
                "full": m.team_partial,
                "restricted": m.restricted_partial,
                "tni": m.tni if not math.isnan(m.tni) else 0.0,
                "category": _task_category(m.task_id),
            }
        model_task_stats[model] = task_stats

    return model_task_stats


# ---------------------------------------------------------------------------
# Per-category aggregation
# ---------------------------------------------------------------------------

def compute_category_stats(
    model_task_stats: dict[str, dict[str, dict]]
) -> dict[str, dict]:
    """
    Aggregate per-task stats into per-category stats across all models.

    Returns: {category: {"mean_uplift": ..., "mean_planning_value": ...,
                         "mean_verification_value": ..., "n_tasks": ...,
                         "n_models": ..., "std_uplift": ...,
                         "archetype": ..., "task_ids": [...]}}
    """
    # Collect per-category, across all models, deduplicating by (task_id)
    cat_data: dict[str, dict] = defaultdict(lambda: {
        "uplifts": [], "planning_values": [], "verification_values": [],
        "oracles": [], "fulls": [], "task_ids": set(), "model_task_uplifts": defaultdict(list),
    })

    for model, task_stats in model_task_stats.items():
        for task_id, stats in task_stats.items():
            cat = stats["category"]
            cat_data[cat]["uplifts"].append(stats["uplift"])
            cat_data[cat]["planning_values"].append(stats["planning_value"])
            cat_data[cat]["verification_values"].append(stats["verification_value"])
            cat_data[cat]["oracles"].append(stats["oracle"])
            cat_data[cat]["fulls"].append(stats["full"])
            cat_data[cat]["task_ids"].add(task_id)
            cat_data[cat]["model_task_uplifts"][model].append(stats["uplift"])

    result: dict[str, dict] = {}
    for cat, d in cat_data.items():
        uplifts = d["uplifts"]
        n = len(uplifts)
        mean_u = float(np.mean(uplifts)) if n else 0.0
        std_u = float(np.std(uplifts)) if n > 1 else 0.0
        mean_pv = float(np.mean(d["planning_values"])) if d["planning_values"] else 0.0
        mean_vv = float(np.mean(d["verification_values"])) if d["verification_values"] else 0.0
        mean_oracle = float(np.mean(d["oracles"])) if d["oracles"] else 0.0

        # Classify team-benefit profile
        if mean_u > 0.05:
            profile = "team-positive"
        elif mean_u < -0.05:
            profile = "team-negative"
        else:
            profile = "team-neutral"

        archetype = ARCHETYPE_MAP.get(cat, "relay")
        result[cat] = {
            "mean_uplift": mean_u,
            "std_uplift": std_u,
            "mean_planning_value": mean_pv,
            "mean_verification_value": mean_vv,
            "mean_oracle": mean_oracle,
            "n_obs": n,
            "n_tasks": len(d["task_ids"]),
            "n_models": len(d["model_task_uplifts"]),
            "profile": profile,
            "archetype": archetype,
            "task_ids": sorted(d["task_ids"]),
            # per-model mean uplift (for cross-model correlation)
            "model_mean_uplifts": {
                m: float(np.mean(vs)) for m, vs in d["model_task_uplifts"].items()
            },
        }

    return result


# ---------------------------------------------------------------------------
# Cross-category correlation matrix
# ---------------------------------------------------------------------------

def compute_cross_category_correlation(
    model_task_stats: dict[str, dict[str, dict]],
    category_stats: dict[str, dict],
) -> dict[str, dict[str, float]]:
    """
    For each pair of categories (A, B), compute Pearson correlation of team uplift.

    Strategy:
    - If multiple models: for each model, compute (mean_uplift_A, mean_uplift_B).
      Correlate across models.
    - If single model (or category appears in only one model): correlate
      per-task uplifts where tasks from A and B can be compared.  When this
      is impossible (different task sets, no natural pairing), fall back to
      a point-biserial: how does individual task uplift in A relate to
      individual task uplift in B at the model level?

    Returns: {cat_A: {cat_B: pearson_r}}  (NaN when n < 3)
    """
    categories = sorted(category_stats.keys())
    n_models = len(model_task_stats)

    corr: dict[str, dict[str, float]] = {c: {} for c in categories}

    # Build model-level vectors: {model -> {category -> mean_uplift}}
    model_cat_uplift: dict[str, dict[str, float]] = {}
    for model, task_stats in model_task_stats.items():
        cat_uplifts: dict[str, list[float]] = defaultdict(list)
        for task_id, stats in task_stats.items():
            cat_uplifts[stats["category"]].append(stats["uplift"])
        model_cat_uplift[model] = {
            cat: float(np.mean(vs)) for cat, vs in cat_uplifts.items()
        }

    for i, cat_a in enumerate(categories):
        for j, cat_b in enumerate(categories):
            if i == j:
                corr[cat_a][cat_b] = 1.0
                continue
            if cat_b in corr[cat_a] and cat_a in corr[cat_b]:
                corr[cat_a][cat_b] = corr[cat_b][cat_a]
                continue

            # Collect (uplift_A, uplift_B) pairs across models
            pairs_a, pairs_b = [], []
            for model, cat_means in model_cat_uplift.items():
                if cat_a in cat_means and cat_b in cat_means:
                    pairs_a.append(cat_means[cat_a])
                    pairs_b.append(cat_means[cat_b])

            if len(pairs_a) >= 3:
                try:
                    r, _ = pearsonr(pairs_a, pairs_b)
                    corr[cat_a][cat_b] = float(r)
                except Exception:
                    corr[cat_a][cat_b] = float("nan")
            else:
                # Fallback: per-task uplifts pooled across models
                all_a, all_b = [], []
                for model, task_stats in model_task_stats.items():
                    a_vals = [s["uplift"] for s in task_stats.values()
                              if s["category"] == cat_a]
                    b_vals = [s["uplift"] for s in task_stats.values()
                              if s["category"] == cat_b]
                    all_a.extend(a_vals)
                    all_b.extend(b_vals)

                # Point-biserial: mean uplift of cat_a tasks vs mean of cat_b tasks
                # Not a per-task pairing — just report NaN for single-model,
                # single-point cases
                if len(all_a) >= 2 and len(all_b) >= 2 and n_models < 3:
                    # With few models, cross-category correlation is unreliable
                    corr[cat_a][cat_b] = float("nan")
                elif len(all_a) >= 3 and len(all_b) >= 3:
                    # Correlate individual task uplifts (same model, diff categories)
                    # This tests: do models that show high uplift on any task in A
                    # also show high uplift on tasks in B?
                    # We pair tasks by their position-within-model rank
                    # (simplified: Pearson of mean(A) vs mean(B) per model)
                    corr[cat_a][cat_b] = float("nan")
                else:
                    corr[cat_a][cat_b] = float("nan")

    return corr


# ---------------------------------------------------------------------------
# Hierarchical clustering
# ---------------------------------------------------------------------------

def cluster_categories(
    category_stats: dict[str, dict],
    n_clusters: int = 4,
) -> dict[str, dict]:
    """
    Cluster categories by their team-benefit profile using hierarchical clustering.

    Feature matrix: [mean_uplift, planning_value, verification_value, mean_oracle]
    Method: Ward linkage on Euclidean distance.

    Returns: {category: {"cluster_id": int, "cluster_label": str, ...}}
    """
    categories = sorted(category_stats.keys())
    if len(categories) < 3:
        return {cat: {"cluster_id": 0, "cluster_label": "unknown"} for cat in categories}

    # Build feature matrix
    X = np.array([
        [
            category_stats[cat]["mean_uplift"],
            category_stats[cat]["mean_planning_value"],
            category_stats[cat]["mean_verification_value"],
            category_stats[cat]["mean_oracle"],
        ]
        for cat in categories
    ], dtype=float)

    # Standardise features (avoid NaN)
    X = np.nan_to_num(X, nan=0.0)
    col_std = X.std(axis=0)
    col_std[col_std < 1e-9] = 1.0
    X_scaled = (X - X.mean(axis=0)) / col_std

    actual_clusters = min(n_clusters, len(categories))
    try:
        Z = linkage(X_scaled, method="ward")
        labels = fcluster(Z, t=actual_clusters, criterion="maxclust")
    except Exception:
        labels = np.ones(len(categories), dtype=int)

    # Assign human-readable cluster labels based on mean uplift within cluster
    cluster_uplifts: dict[int, list[float]] = defaultdict(list)
    for cat, label in zip(categories, labels):
        cluster_uplifts[int(label)].append(category_stats[cat]["mean_uplift"])

    cluster_mean = {cid: float(np.mean(vs)) for cid, vs in cluster_uplifts.items()}
    sorted_clusters = sorted(cluster_mean.items(), key=lambda kv: kv[1], reverse=True)
    label_names = ["team-positive", "team-moderate", "team-neutral", "team-negative"]
    cluster_name = {
        cid: label_names[min(rank, len(label_names) - 1)]
        for rank, (cid, _) in enumerate(sorted_clusters)
    }

    result: dict[str, dict] = {}
    for cat, label in zip(categories, labels):
        result[cat] = {
            "cluster_id": int(label),
            "cluster_label": cluster_name.get(int(label), "unknown"),
            "features": {
                "mean_uplift": category_stats[cat]["mean_uplift"],
                "planning_value": category_stats[cat]["mean_planning_value"],
                "verification_value": category_stats[cat]["mean_verification_value"],
                "mean_oracle": category_stats[cat]["mean_oracle"],
            },
        }

    return result


# ---------------------------------------------------------------------------
# Archetype analysis
# ---------------------------------------------------------------------------

def analyze_archetypes(
    model_task_stats: dict[str, dict[str, dict]],
    category_stats: dict[str, dict],
) -> dict[str, dict]:
    """
    Compute mean uplift per archetype and compare R² of archetype vs category
    in predicting task-level uplift.

    Returns: {archetype: {"mean_uplift": ..., "std_uplift": ..., "n_tasks": ...,
                          "categories": [...]}}
             plus "r2_archetype" and "r2_category" at top level.
    """
    # Collect per-task (uplift, archetype, category) across all models
    task_uplifts: list[tuple[float, str, str]] = []
    for model, task_stats in model_task_stats.items():
        for task_id, stats in task_stats.items():
            cat = stats["category"]
            arch = ARCHETYPE_MAP.get(cat, "relay")
            task_uplifts.append((stats["uplift"], arch, cat))

    if not task_uplifts:
        return {}

    uplifts_arr = np.array([t[0] for t in task_uplifts])
    archetypes_list = [t[1] for t in task_uplifts]
    categories_list = [t[2] for t in task_uplifts]

    # R² for archetype (one-way ANOVA style: between-group SS / total SS)
    def r2_from_groups(labels: list[str], values: np.ndarray) -> float:
        grand_mean = float(values.mean())
        total_ss = float(((values - grand_mean) ** 2).sum())
        if total_ss < 1e-12:
            return 0.0
        between_ss = 0.0
        unique_labels = set(labels)
        for lbl in unique_labels:
            mask = np.array([l == lbl for l in labels])
            group = values[mask]
            if len(group) == 0:
                continue
            between_ss += len(group) * (float(group.mean()) - grand_mean) ** 2
        return float(between_ss / total_ss)

    r2_archetype = r2_from_groups(archetypes_list, uplifts_arr)
    r2_category = r2_from_groups(categories_list, uplifts_arr)

    # Per-archetype stats
    arch_data: dict[str, dict] = {}
    for arch in ARCHETYPES:
        mask = np.array([a == arch for a in archetypes_list])
        if not mask.any():
            continue
        vals = uplifts_arr[mask]
        cats = sorted({c for a, c in zip(archetypes_list, categories_list) if a == arch})
        arch_data[arch] = {
            "mean_uplift": float(vals.mean()),
            "std_uplift": float(vals.std()) if len(vals) > 1 else 0.0,
            "n_obs": int(mask.sum()),
            "categories": cats,
        }

    arch_data["_r2_archetype"] = r2_archetype  # type: ignore[assignment]
    arch_data["_r2_category"] = r2_category    # type: ignore[assignment]
    arch_data["_archetype_is_better_predictor"] = r2_archetype > r2_category  # type: ignore[assignment]

    return arch_data


# ---------------------------------------------------------------------------
# Transfer prediction (leave-one-category-out)
# ---------------------------------------------------------------------------

def transfer_prediction(
    category_stats: dict[str, dict],
) -> dict[str, float]:
    """
    Leave-one-category-out cross-validation: predict held-out category's
    mean uplift from other categories' summary features.

    Features (per category): mean_oracle, n_tasks, archetype (one-hot),
                              mean_planning_value, mean_verification_value
    Target: mean_uplift

    Predictor: weighted-mean of training categories' uplifts, weighted by
    cosine similarity of feature vectors (k-NN style with k=all, inverse-distance).

    Returns: {"cv_r2": float, "mae": float, "predictions": {cat: pred}}
    """
    categories = sorted(category_stats.keys())
    n = len(categories)
    if n < 4:
        return {"cv_r2": float("nan"), "mae": float("nan"), "predictions": {}}

    # Build feature vectors
    arch_idx = {a: i for i, a in enumerate(ARCHETYPES)}

    def feat(cat: str) -> np.ndarray:
        s = category_stats[cat]
        arch = ARCHETYPE_MAP.get(cat, "relay")
        one_hot = np.zeros(len(ARCHETYPES))
        one_hot[arch_idx.get(arch, 0)] = 1.0
        return np.array([
            s["mean_oracle"],
            s["n_tasks"] / 10.0,   # normalise
            s["mean_planning_value"],
            s["mean_verification_value"],
        ] + list(one_hot), dtype=float)

    X = np.array([feat(c) for c in categories])
    y = np.array([category_stats[c]["mean_uplift"] for c in categories])

    # Standardise
    col_std = X.std(axis=0)
    col_std[col_std < 1e-9] = 1.0
    X_scaled = (X - X.mean(axis=0)) / col_std

    # LOOCV with inverse-distance weighted kNN (all neighbours)
    preds = np.zeros(n)
    for i in range(n):
        train_X = np.delete(X_scaled, i, axis=0)
        train_y = np.delete(y, i)
        test_x = X_scaled[i]

        dists = np.linalg.norm(train_X - test_x, axis=1)
        dists = np.maximum(dists, 1e-9)
        weights = 1.0 / dists
        preds[i] = float(np.average(train_y, weights=weights))

    residuals = y - preds
    ss_res = float((residuals ** 2).sum())
    ss_tot = float(((y - y.mean()) ** 2).sum())
    cv_r2 = 1.0 - ss_res / ss_tot if ss_tot > 1e-12 else float("nan")
    mae = float(np.abs(residuals).mean())

    return {
        "cv_r2": cv_r2,
        "mae": mae,
        "predictions": {c: float(p) for c, p in zip(categories, preds)},
    }


# ---------------------------------------------------------------------------
# Output generation
# ---------------------------------------------------------------------------

def _fmt(v: float, decimals: int = 3) -> str:
    if math.isnan(v):
        return "—"
    return f"{v:+.{decimals}f}" if v != 0 else f"{v:.{decimals}f}"


def generate_latex_heatmap(
    categories: list[str],
    corr: dict[str, dict[str, float]],
    cluster_info: dict[str, dict],
) -> str:
    """Generate a compact LaTeX correlation heatmap table."""
    # Use short display names
    def short(cat: str) -> str:
        return CATEGORY_DISPLAY.get(cat, cat[:6])

    cats = [c for c in categories if c in corr]
    n = len(cats)
    if n == 0:
        return "% No data for cross-category correlation table\n"

    col_spec = "l" + "r" * n
    lines = [
        "% Auto-generated by scripts/cross_domain_analysis.py",
        "\\begin{table}[t]",
        "\\centering",
        "\\small",
        "\\caption{Cross-category team-uplift correlation. "
        "Entries show Pearson $r$ of mean team uplift across models. "
        "Bold = $|r| > 0.5$. Categories sorted by mean uplift descending.}",
        f"\\begin{{tabular}}{{{col_spec}}}",
        "\\toprule",
    ]

    # Header row
    header = " & " + " & ".join(f"\\rotatebox{{60}}{{{short(c)}}}" for c in cats) + " \\\\"
    lines.append(header)
    lines.append("\\midrule")

    for cat_a in cats:
        clbl = cluster_info.get(cat_a, {}).get("cluster_label", "")
        marker = "*" if "positive" in clbl else ("†" if "negative" in clbl else "")
        row_parts = [f"{short(cat_a)}{marker}"]
        for cat_b in cats:
            r = corr.get(cat_a, {}).get(cat_b, float("nan"))
            if math.isnan(r):
                cell = "—"
            elif cat_a == cat_b:
                cell = "1.00"
            else:
                s = f"{r:+.2f}"
                cell = f"\\textbf{{{s}}}" if abs(r) > 0.5 else s
            row_parts.append(cell)
        lines.append(" & ".join(row_parts) + " \\\\")

    lines += [
        "\\bottomrule",
        "\\multicolumn{" + str(n + 1) + "}{l}{\\footnotesize "
        "$^*$team-positive ($\\uparrow>0.05$); "
        "$^\\dagger$team-negative ($\\downarrow<-0.05$)}",
        "\\end{tabular}",
        "\\end{table}",
    ]
    return "\n".join(lines) + "\n"


def generate_csv(
    categories: list[str],
    category_stats: dict[str, dict],
    corr: dict[str, dict[str, float]],
    cluster_info: dict[str, dict],
) -> str:
    """Generate CSV for heatmap visualization."""
    cats = [c for c in categories if c in corr]
    rows = ["category_a,category_b,pearson_r,cat_a_uplift,cat_b_uplift,"
            "cat_a_archetype,cat_b_archetype,cat_a_cluster,cat_b_cluster"]
    for cat_a in cats:
        for cat_b in cats:
            r = corr.get(cat_a, {}).get(cat_b, float("nan"))
            r_str = f"{r:.4f}" if not math.isnan(r) else ""
            ua = category_stats.get(cat_a, {}).get("mean_uplift", float("nan"))
            ub = category_stats.get(cat_b, {}).get("mean_uplift", float("nan"))
            aa = ARCHETYPE_MAP.get(cat_a, "relay")
            ab = ARCHETYPE_MAP.get(cat_b, "relay")
            ca = cluster_info.get(cat_a, {}).get("cluster_label", "")
            cb = cluster_info.get(cat_b, {}).get("cluster_label", "")
            rows.append(
                f"{cat_a},{cat_b},{r_str},"
                f"{ua:.4f},{ub:.4f},{aa},{ab},{ca},{cb}"
            )
    return "\n".join(rows) + "\n"


def print_summary(
    category_stats: dict[str, dict],
    cluster_info: dict[str, dict],
    archetype_stats: dict[str, dict],
    transfer: dict[str, float],
    corr: dict[str, dict[str, float]],
) -> None:
    """Print human-readable summary to stdout."""
    print("\n" + "=" * 70)
    print("CROSS-DOMAIN ANALYSIS SUMMARY")
    print("=" * 70)

    # Per-category team uplift
    print("\n--- Per-Category Team Uplift (mean full - oracle) ---")
    sorted_cats = sorted(category_stats.items(), key=lambda kv: kv[1]["mean_uplift"], reverse=True)
    for cat, s in sorted_cats:
        clbl = cluster_info.get(cat, {}).get("cluster_label", "")
        arch = s["archetype"]
        bar = "+" * max(0, int(s["mean_uplift"] * 20)) if s["mean_uplift"] > 0 else \
              "-" * max(0, int(-s["mean_uplift"] * 20))
        print(f"  {cat:<22} uplift={s['mean_uplift']:+.3f}  ({clbl:<16})  "
              f"arch={arch:<12}  n={s['n_obs']:>3}  {bar}")

    # Cluster groupings
    print("\n--- Cluster Groupings ---")
    from collections import defaultdict as dd
    clusters: dict[str, list[str]] = dd(list)
    for cat, info in cluster_info.items():
        clusters[info["cluster_label"]].append(cat)
    for lbl, cats in sorted(clusters.items()):
        print(f"  {lbl}: {', '.join(sorted(cats))}")

    # Archetype analysis
    r2_arch = archetype_stats.get("_r2_archetype", float("nan"))
    r2_cat = archetype_stats.get("_r2_category", float("nan"))
    better = archetype_stats.get("_archetype_is_better_predictor", False)
    print(f"\n--- Archetype Analysis ---")
    print(f"  R² archetype: {r2_arch:.3f}   R² category: {r2_cat:.3f}")
    print(f"  Archetype {'IS' if better else 'is NOT'} a better predictor of uplift than category")
    for arch in ARCHETYPES:
        if arch in archetype_stats:
            s = archetype_stats[arch]
            print(f"  {arch:<14}  mean_uplift={s['mean_uplift']:+.3f}  "
                  f"n={s['n_obs']:>3}  cats={', '.join(s['categories'])}")

    # Transfer prediction
    cv_r2 = transfer.get("cv_r2", float("nan"))
    mae = transfer.get("mae", float("nan"))
    print(f"\n--- Transfer Prediction (LOOCV, kNN) ---")
    print(f"  Cross-validated R²: {cv_r2:.3f}")
    print(f"  MAE: {mae:.3f}")
    if not math.isnan(cv_r2):
        if cv_r2 > 0.5:
            print("  Interpretation: strong transferability — known categories can "
                  "predict new ones")
        elif cv_r2 > 0.2:
            print("  Interpretation: moderate transferability")
        else:
            print("  Interpretation: weak transferability — each category is largely independent")

    # Notable cross-category correlations
    print("\n--- Notable Cross-Category Correlations (|r| > 0.4) ---")
    found_any = False
    cats = sorted(category_stats.keys())
    for i, ca in enumerate(cats):
        for j, cb in enumerate(cats):
            if j <= i:
                continue
            r = corr.get(ca, {}).get(cb, float("nan"))
            if not math.isnan(r) and abs(r) > 0.4:
                found_any = True
                print(f"  {ca} ↔ {cb}: r={r:+.3f}")
    if not found_any:
        print("  (none above threshold — categories appear largely independent)")

    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="TeamBench cross-domain analysis")
    parser.add_argument(
        "--ablation-dir",
        default="shared/ablation_results",
        help="Directory containing ablation JSON files",
    )
    parser.add_argument(
        "--output-dir",
        default="shared/paper",
        help="Directory for output files",
    )
    parser.add_argument(
        "--n-clusters",
        type=int,
        default=4,
        help="Number of hierarchical clusters",
    )
    args = parser.parse_args()

    ablation_dir = args.ablation_dir
    output_dir = args.output_dir
    os.makedirs(output_dir, exist_ok=True)

    # 1. Load data
    print(f"Loading ablation data from {ablation_dir} ...")
    model_runs = load_all_runs(ablation_dir)
    if not model_runs:
        print("ERROR: No runs loaded. Check --ablation-dir path.")
        sys.exit(1)

    # 2. Compute per-task uplifts
    model_task_stats = compute_task_uplifts(model_runs)
    n_tasks_total = sum(len(ts) for ts in model_task_stats.values())
    print(f"Computed uplifts for {n_tasks_total} (model, task) pairs")

    # 3. Per-category aggregation
    category_stats = compute_category_stats(model_task_stats)
    print(f"Categories found: {sorted(category_stats.keys())}")

    # 4. Cross-category correlation matrix
    corr = compute_cross_category_correlation(model_task_stats, category_stats)

    # 5. Cluster analysis
    cluster_info = cluster_categories(category_stats, n_clusters=args.n_clusters)

    # 6. Archetype analysis
    archetype_stats = analyze_archetypes(model_task_stats, category_stats)

    # 7. Transfer prediction
    transfer = transfer_prediction(category_stats)

    # Print summary
    print_summary(category_stats, cluster_info, archetype_stats, transfer, corr)

    # Sort categories by mean uplift descending for outputs
    sorted_cats = sorted(category_stats.keys(),
                         key=lambda c: category_stats[c]["mean_uplift"], reverse=True)

    # --- Output 1: JSON ---
    json_out = {
        "category_stats": {
            cat: {k: v for k, v in category_stats[cat].items() if k != "task_ids"}
            | {"task_ids": category_stats[cat]["task_ids"]}
            for cat in sorted_cats
        },
        "cross_category_correlation": {
            cat_a: {cat_b: (None if math.isnan(v) else v)
                    for cat_b, v in corr[cat_a].items()}
            for cat_a in sorted_cats if cat_a in corr
        },
        "cluster_info": {
            cat: cluster_info.get(cat, {}) for cat in sorted_cats
        },
        "archetype_stats": {
            k: v for k, v in archetype_stats.items()
            if not k.startswith("_")
        },
        "archetype_r2": archetype_stats.get("_r2_archetype", None),
        "category_r2": archetype_stats.get("_r2_category", None),
        "archetype_better_predictor": archetype_stats.get(
            "_archetype_is_better_predictor", None),
        "transfer_prediction": transfer,
        "n_models": len(model_runs),
        "model_names": sorted(model_runs.keys()),
    }
    json_path = os.path.join(output_dir, "cross_domain_analysis.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_out, f, indent=2, default=str)
    print(f"Wrote {json_path}")

    # --- Output 2: LaTeX table ---
    latex = generate_latex_heatmap(sorted_cats, corr, cluster_info)
    tex_path = os.path.join(output_dir, "table_cross_domain.tex")
    with open(tex_path, "w", encoding="utf-8") as f:
        f.write(latex)
    print(f"Wrote {tex_path}")

    # --- Output 3: CSV for visualization ---
    csv_data = generate_csv(sorted_cats, category_stats, corr, cluster_info)
    csv_path = os.path.join(output_dir, "fig_cross_domain.csv")
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write(csv_data)
    print(f"Wrote {csv_path}")


if __name__ == "__main__":
    main()
