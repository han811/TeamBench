#!/usr/bin/env python3
"""
verification_deep_dive.py — Verification Accuracy failure mode taxonomy.

Compares full_team vs team_no_verify across all ablation runs to classify
every task into verification failure modes and compute per-category/difficulty stats.

Outputs:
  shared/paper/verification_deep_dive.json
  shared/paper/table_verification_taxonomy.tex
  shared/paper/table_verification_by_category.tex
"""

import json
import os
import glob
import re
from collections import defaultdict
from typing import Any

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ABLATION_DIR = os.path.join(REPO_ROOT, "shared", "ablation_results")
TASKS_DIR = os.path.join(REPO_ROOT, "tasks")
PAPER_DIR = os.path.join(REPO_ROOT, "shared", "paper")
os.makedirs(PAPER_DIR, exist_ok=True)

# Score tolerance for "neutral" classification
NEUTRAL_TOL = 0.02

# ---------------------------------------------------------------------------
# 1. Load ablation data (deduplicated by task_id + condition + seed)
# ---------------------------------------------------------------------------

# Priority order: phase3 seeds 1&2 extend canonical; crossmodel adds cross-model g3flash
# Use latest record when duplicate (task, condition, seed) keys appear.
CANONICAL_FILES = [
    "batch1_swe_data_seed0_g3flash.json",
    "batch2_sec_policy_neg_seed0_g3flash.json",
    "batch3_inc_ops_seed0_g3flash.json",
    "batch4_test_spec_cr_seed0_g3flash.json",
    "batch5_lh_pipe_ir_multi_int_seed0_g3flash.json",
    "batch6_trap_cross_crypto_dist_go_js_seed0_g3flash.json",
    "crypto_dist_g3flash.json",
    "trap_cross_g3flash.json",
    "phase3_all_consolidated.json",
    "crossmodel_g3flash_seed0.json",
]


def load_all_runs() -> list[dict]:
    """Load and deduplicate runs from canonical ablation files."""
    seen: dict[tuple, dict] = {}  # (task_id, condition, seed) -> run

    for fname in CANONICAL_FILES:
        fpath = os.path.join(ABLATION_DIR, fname)
        if not os.path.exists(fpath):
            print(f"  [WARN] missing: {fname}")
            continue
        with open(fpath) as f:
            data = json.load(f)
        runs = data.get("runs", [])
        if not isinstance(runs, list):
            continue
        for r in runs:
            if "condition" not in r:
                continue
            key = (r["task_id"], r["condition"], r.get("seed", 0))
            seen[key] = r  # last write wins

    return list(seen.values())


# ---------------------------------------------------------------------------
# 2. Build task metadata (category, difficulty) from task.yaml files
# ---------------------------------------------------------------------------

def parse_task_yaml_simple(path: str) -> dict[str, str]:
    """Minimal YAML key:value parser (avoids pyyaml dependency for flat keys)."""
    meta: dict[str, str] = {}
    with open(path) as f:
        for line in f:
            line = line.rstrip()
            if not line or line.lstrip().startswith("#") or line.startswith(" ") or line.startswith("\t"):
                continue
            if ":" in line:
                k, _, v = line.partition(":")
                meta[k.strip()] = v.strip().strip("\"'")
    return meta


def infer_category(task_id: str) -> str:
    """Infer canonical category from task_id prefix if task.yaml not available."""
    prefix = re.match(r"^([A-Z]+)\d*_", task_id)
    if prefix:
        p = prefix.group(1)
        mapping = {
            "SEC": "Security", "TRAP": "Adversarial", "CROSS": "Cross-System",
            "CRYPTO": "Cryptographic", "DIST": "Distributed", "TEST": "Testing",
            "SPEC": "Specification", "CR": "Code Review", "LH": "Long Horizon",
            "PIPE": "Pipeline", "INC": "Incident", "IR": "Info Retrieval",
            "MULTI": "Multi-Language", "INT": "Integration", "NEG": "Negotiation",
            "OPS": "Operations", "O": "Operations", "S": "Software",
            "D": "Data", "P": "Policy", "GH": "Real-World/GH",
            "RDS": "Data Science", "DS": "Data Science",
            "RINC": "Incident", "GO": "Go", "JS": "JavaScript",
            "SQL": "SQL", "EA": "Expertise Asymmetry", "API": "API",
        }
        return mapping.get(p, p)
    return "Unknown"


# Normalize free-form category strings from task.yaml to canonical names
_CATEGORY_NORM: dict[str, str] = {
    # Security
    "security": "Security",
    # Incident
    "incident": "Incident", "incident_response": "Incident",
    "Incident-Response": "Incident", "Incident-response": "Incident",
    # Operations
    "operations": "Operations", "ops": "Operations",
    "Ops": "Operations", "ops_perf": "Operations",
    # Software / SWE
    "software": "Software", "swe": "Software", "SWE": "Software",
    "engineering": "Software", "Software Engineering": "Software",
    # Data
    "data": "Data", "Data Engineering": "Data", "DataEngineering": "Data",
    # Data Science
    "data_science": "Data Science",
    # Pipeline / Integration
    "pipeline": "Pipeline", "Pipeline/Integration": "Pipeline",
    # Information Retrieval
    "ir": "Info Retrieval", "information_retrieval": "Info Retrieval",
    "Information-Retrieval": "Info Retrieval",
    # Multi-language
    "multi_language": "Multi-Language",
    # Code Review
    "code_review": "Code Review", "CodeReview": "Code Review",
    # Long Horizon
    "long": "Long Horizon", "long_horizon": "Long Horizon",
    # Policy
    "policy": "Policy",
    # Testing
    "testing": "Testing",
    # Config / misc
    "config": "Configuration", "debugging": "Debugging",
    "Performance": "Performance",
    # Real-World
    "Real-World GitHub": "Real-World/GH",
    # javascript
    "javascript": "JavaScript",
}


def normalize_category(raw: str) -> str:
    """Map free-form category string to a canonical label."""
    return _CATEGORY_NORM.get(raw, raw)


def load_task_metadata() -> dict[str, dict[str, str]]:
    """Return {task_id: {category, difficulty, domain}} for all tasks with task.yaml."""
    meta: dict[str, dict[str, str]] = {}
    if not os.path.isdir(TASKS_DIR):
        return meta
    for td in os.listdir(TASKS_DIR):
        yp = os.path.join(TASKS_DIR, td, "task.yaml")
        if not os.path.exists(yp):
            continue
        try:
            raw = parse_task_yaml_simple(yp)
        except Exception:
            continue
        cat = raw.get("category") or raw.get("domain") or infer_category(td)
        diff = raw.get("difficulty", "unknown")
        meta[td] = {"category": cat, "difficulty": diff}
    return meta


# ---------------------------------------------------------------------------
# 3. Per-task score aggregation
# ---------------------------------------------------------------------------

def aggregate_per_task(runs: list[dict]) -> dict[str, dict[str, Any]]:
    """
    For each (task_id, seed) group, collect scores per condition.
    Returns {task_id: {seed: {condition: {pass, partial_score, failure_modes}}}}
    """
    by_task: dict[str, dict] = defaultdict(lambda: defaultdict(dict))
    for r in runs:
        tid = r["task_id"]
        seed = r.get("seed", 0)
        cond = r["condition"]
        by_task[tid][seed][cond] = {
            "pass": bool(r.get("pass", False)),
            "partial_score": float(r.get("partial_score") or 0.0),
            "failure_modes": r.get("failure_modes") or [],
            "elapsed_sec": r.get("elapsed_sec"),
        }
    return {k: dict(v) for k, v in by_task.items()}


# ---------------------------------------------------------------------------
# 4. Failure mode taxonomy classification
# ---------------------------------------------------------------------------

FAILURE_MODES = [
    "true_positive",       # verifier caught real issue; full > no_verify AND full >= oracle
    "true_negative",       # both pass; verifier correctly approved
    "false_rejection",     # verifier rejected correct work; full < no_verify
    "hallucinated_req",    # no_verify passes but full fails (strong false rejection)
    "verification_neutral",# full ≈ no_verify (±tol), not clearly pass
    "insufficient_data",   # missing conditions
]


def classify_observation(full: float, no_verify: float, oracle: float,
                         full_pass: bool, nv_pass: bool, oracle_pass: bool) -> str:
    diff = full - no_verify

    if abs(diff) <= NEUTRAL_TOL:
        if full_pass and nv_pass:
            return "true_negative"
        return "verification_neutral"

    if diff > NEUTRAL_TOL:
        # Verification helped
        return "true_positive"

    # diff < -NEUTRAL_TOL: verification hurt
    if nv_pass and not full_pass:
        return "hallucinated_req"
    return "false_rejection"


def classify_task(task_id: str, seeds_data: dict) -> dict[str, Any]:
    """
    Classify a task across all available seeds.
    Returns per-seed classifications + aggregate summary.
    """
    per_seed = {}
    score_drops = []
    score_lifts = []

    for seed, cond_data in sorted(seeds_data.items()):
        full = cond_data.get("full")
        nv = cond_data.get("team_no_verify")
        orc = cond_data.get("oracle")

        if full is None or nv is None:
            per_seed[seed] = {"classification": "insufficient_data"}
            continue

        full_score = full["partial_score"]
        nv_score = nv["partial_score"]
        orc_score = orc["partial_score"] if orc else full_score  # fallback

        cls = classify_observation(
            full=full_score,
            no_verify=nv_score,
            oracle=orc_score,
            full_pass=full["pass"],
            nv_pass=nv["pass"],
            oracle_pass=orc["pass"] if orc else False,
        )

        drop = nv_score - full_score  # positive = verification hurt
        per_seed[seed] = {
            "classification": cls,
            "full_score": full_score,
            "nv_score": nv_score,
            "oracle_score": orc_score,
            "full_pass": full["pass"],
            "nv_pass": nv["pass"],
            "score_delta": full_score - nv_score,  # positive = helped
            "failure_modes_full": full["failure_modes"],
        }

        if drop > NEUTRAL_TOL:
            score_drops.append(drop)
        elif full_score - nv_score > NEUTRAL_TOL:
            score_lifts.append(full_score - nv_score)

    # Aggregate classification: majority vote
    valid_cls = [v["classification"] for v in per_seed.values()
                 if v["classification"] != "insufficient_data"]
    if not valid_cls:
        agg_cls = "insufficient_data"
    else:
        from collections import Counter
        agg_cls = Counter(valid_cls).most_common(1)[0][0]

    mean_drop = sum(score_drops) / len(score_drops) if score_drops else 0.0
    mean_lift = sum(score_lifts) / len(score_lifts) if score_lifts else 0.0
    n_hurt = len(score_drops)
    n_helped = len(score_lifts)

    return {
        "task_id": task_id,
        "aggregate_classification": agg_cls,
        "per_seed": per_seed,
        "n_seeds": len(per_seed),
        "n_hurt": n_hurt,
        "n_helped": n_helped,
        "mean_score_drop_when_hurt": round(mean_drop, 4),
        "mean_score_lift_when_helped": round(mean_lift, 4),
    }


# ---------------------------------------------------------------------------
# 5. Difficulty quintile assignment (empirical, from oracle score)
# ---------------------------------------------------------------------------

def assign_difficulty_quintiles(task_results: dict[str, dict],
                                 task_data: dict[str, dict]) -> dict[str, str]:
    """Assign difficulty quintile based on oracle partial score."""
    scores = {}
    for tid, info in task_data.items():
        oracle_scores = []
        for seed_data in info.items() if isinstance(info, dict) else []:
            pass
        # collect oracle scores across seeds
        for seed, cond_data in info.items():
            orc = cond_data.get("oracle")
            if orc:
                oracle_scores.append(orc["partial_score"])
        if oracle_scores:
            scores[tid] = sum(oracle_scores) / len(oracle_scores)

    if not scores:
        return {}

    sorted_tasks = sorted(scores.keys(), key=lambda t: scores[t])
    n = len(sorted_tasks)
    quintile_labels = ["Q1_hardest", "Q2_hard", "Q3_medium", "Q4_easy", "Q5_easiest"]
    quintile_map = {}
    for i, tid in enumerate(sorted_tasks):
        q_idx = min(int(i / n * 5), 4)
        quintile_map[tid] = quintile_labels[q_idx]
    return quintile_map


# ---------------------------------------------------------------------------
# 6. Main analysis
# ---------------------------------------------------------------------------

def run_analysis() -> dict[str, Any]:
    print("Loading runs...")
    runs = load_all_runs()
    print(f"  {len(runs)} deduplicated runs")

    print("Loading task metadata...")
    task_meta = load_task_metadata()

    print("Aggregating per task...")
    per_task_data = aggregate_per_task(runs)
    print(f"  {len(per_task_data)} unique tasks")

    # Classify each task
    task_results = {}
    for tid, seeds_data in per_task_data.items():
        task_results[tid] = classify_task(tid, seeds_data)

    # Assign difficulty quintiles
    quintile_map = assign_difficulty_quintiles(task_results, per_task_data)

    # Enrich with metadata
    for tid, result in task_results.items():
        meta = task_meta.get(tid, {})
        raw_cat = meta.get("category") or infer_category(tid)
        result["category"] = normalize_category(raw_cat)
        result["difficulty_yaml"] = meta.get("difficulty", "unknown")
        result["difficulty_quintile"] = quintile_map.get(tid, "unknown")

    # ---------------------------------------------------------------------------
    # Aggregate statistics
    # ---------------------------------------------------------------------------
    from collections import Counter

    # Overall taxonomy counts (per-task aggregate classification)
    taxonomy_counts = Counter(r["aggregate_classification"] for r in task_results.values())

    # Per-seed classification counts (more granular, N = n_tasks × n_seeds)
    per_seed_counts = Counter()
    for result in task_results.values():
        for s_data in result["per_seed"].values():
            per_seed_counts[s_data["classification"]] += 1

    # Verification value per task (mean delta across seeds)
    def mean_delta(result: dict) -> float:
        deltas = [v["score_delta"] for v in result["per_seed"].values()
                  if "score_delta" in v]
        return sum(deltas) / len(deltas) if deltas else 0.0

    all_deltas = [mean_delta(r) for r in task_results.values()]
    mean_verif_value = sum(all_deltas) / len(all_deltas) if all_deltas else 0.0

    hurt_tasks = [r for r in task_results.values()
                  if r["aggregate_classification"] in ("false_rejection", "hallucinated_req")]
    helped_tasks = [r for r in task_results.values()
                    if r["aggregate_classification"] == "true_positive"]

    # ---------------------------------------------------------------------------
    # Per-category analysis
    # ---------------------------------------------------------------------------
    cat_stats: dict[str, dict] = defaultdict(lambda: {
        "n_tasks": 0,
        "taxonomy": Counter(),
        "sum_delta": 0.0,
        "n_hurt": 0,
        "n_helped": 0,
        "n_neutral_tn": 0,
    })

    for result in task_results.values():
        cat = result["category"]
        s = cat_stats[cat]
        s["n_tasks"] += 1
        s["taxonomy"][result["aggregate_classification"]] += 1
        s["sum_delta"] += mean_delta(result)
        if result["aggregate_classification"] in ("false_rejection", "hallucinated_req"):
            s["n_hurt"] += 1
        elif result["aggregate_classification"] == "true_positive":
            s["n_helped"] += 1
        else:
            s["n_neutral_tn"] += 1

    for cat, s in cat_stats.items():
        s["mean_verif_value"] = round(s["sum_delta"] / s["n_tasks"], 4) if s["n_tasks"] else 0
        s["taxonomy"] = dict(s["taxonomy"])

    # ---------------------------------------------------------------------------
    # Per-difficulty-quintile analysis
    # ---------------------------------------------------------------------------
    quint_stats: dict[str, dict] = defaultdict(lambda: {
        "n_tasks": 0, "taxonomy": Counter(), "sum_delta": 0.0
    })
    for result in task_results.values():
        q = result["difficulty_quintile"]
        s = quint_stats[q]
        s["n_tasks"] += 1
        s["taxonomy"][result["aggregate_classification"]] += 1
        s["sum_delta"] += mean_delta(result)

    for q, s in quint_stats.items():
        s["mean_verif_value"] = round(s["sum_delta"] / s["n_tasks"], 4) if s["n_tasks"] else 0
        s["taxonomy"] = dict(s["taxonomy"])

    # ---------------------------------------------------------------------------
    # False rejection cost analysis
    # ---------------------------------------------------------------------------
    false_rejection_details = []
    for r in hurt_tasks:
        false_rejection_details.append({
            "task_id": r["task_id"],
            "category": r["category"],
            "classification": r["aggregate_classification"],
            # mean_score_drop_when_hurt is already the magnitude of the drop (positive = bad)
            "mean_score_drop": round(r["mean_score_drop_when_hurt"], 4),
            "n_seeds_hurt": r["n_hurt"],
        })
    false_rejection_details.sort(key=lambda x: -x["mean_score_drop"])

    # Naive heuristic: "accept if executor claims done" = use team_no_verify score
    # Compare: mean(full) vs mean(no_verify) across all tasks
    def cond_mean(condition: str) -> float:
        scores = []
        for tid, seeds_data in per_task_data.items():
            for seed, cond_data in seeds_data.items():
                c = cond_data.get(condition)
                if c:
                    scores.append(c["partial_score"])
        return sum(scores) / len(scores) if scores else 0.0

    mean_full = cond_mean("full")
    mean_nv = cond_mean("team_no_verify")
    mean_oracle = cond_mean("oracle")

    heuristic_gain = mean_nv - mean_full  # positive = no_verify beats full

    # ---------------------------------------------------------------------------
    # Summary
    # ---------------------------------------------------------------------------
    total_tasks = len(task_results)
    summary = {
        "total_tasks_analyzed": total_tasks,
        "total_runs_loaded": len(runs),
        "mean_full_score": round(mean_full, 4),
        "mean_no_verify_score": round(mean_nv, 4),
        "mean_oracle_score": round(mean_oracle, 4),
        "mean_verification_value": round(mean_verif_value, 4),
        "heuristic_gain_no_verify_vs_full": round(heuristic_gain, 4),
        "taxonomy_per_task": dict(taxonomy_counts),
        "taxonomy_per_seed_observation": dict(per_seed_counts),
        "n_tasks_verification_helped": len(helped_tasks),
        "n_tasks_verification_hurt": len(hurt_tasks),
        "n_tasks_neutral_or_tn": total_tasks - len(helped_tasks) - len(hurt_tasks),
        "mean_score_drop_false_rejections": round(
            sum(x["mean_score_drop"] for x in false_rejection_details) / len(false_rejection_details)
            if false_rejection_details else 0.0, 4
        ),
        # fraction of tasks where a naive "skip verification" heuristic would win
        "frac_tasks_nv_better": round(
            sum(1 for r in task_results.values()
                if r["aggregate_classification"] in ("false_rejection", "hallucinated_req"))
            / total_tasks, 4
        ) if total_tasks else 0.0,
    }

    return {
        "summary": summary,
        "per_task": task_results,
        "per_category": {k: dict(v) for k, v in cat_stats.items()},
        "per_difficulty_quintile": {k: dict(v) for k, v in quint_stats.items()},
        "false_rejection_details": false_rejection_details,
    }


# ---------------------------------------------------------------------------
# 7. LaTeX table generators
# ---------------------------------------------------------------------------

def make_taxonomy_table(analysis: dict) -> str:
    summary = analysis["summary"]
    taxonomy = summary["taxonomy_per_task"]
    total = summary["total_tasks_analyzed"]

    fm_labels = {
        "true_positive":        "True Positive (verifier caught real issue)",
        "true_negative":        "True Negative (verifier correctly approved)",
        "false_rejection":      "False Rejection (verifier rejected correct work)",
        "hallucinated_req":     "Hallucinated Requirements (no-verify passes, full fails)",
        "verification_neutral": "Verification Neutral (no meaningful change)",
        "insufficient_data":    "Insufficient Data (missing conditions)",
    }

    rows = []
    for key, label in fm_labels.items():
        n = taxonomy.get(key, 0)
        pct = 100.0 * n / total if total else 0.0
        rows.append((label, n, pct))

    lines = [
        r"\begin{table}[h]",
        r"\centering",
        r"\caption{Verification Failure Mode Taxonomy across " + str(total) + r" tasks}",
        r"\label{tab:verification_taxonomy}",
        r"\begin{tabular}{lrr}",
        r"\toprule",
        r"\textbf{Failure Mode} & \textbf{Tasks} & \textbf{\%} \\",
        r"\midrule",
    ]
    for label, n, pct in rows:
        lines.append(f"{label} & {n} & {pct:.1f}\\% \\\\")

    lines += [
        r"\midrule",
        f"\\textbf{{Total}} & \\textbf{{{total}}} & \\textbf{{100.0\\%}} \\\\",
        r"\bottomrule",
        r"\end{tabular}",
        "",
        r"\smallskip",
        r"\noindent\small",
        r"Mean verification value (full $-$ no\textunderscore verify): "
        + f"{summary['mean_verification_value']:+.3f}. "
        + r"``No-verify'' heuristic gain over full team: "
        + f"{summary['heuristic_gain_no_verify_vs_full']:+.3f}.",
        r"\end{table}",
    ]
    return "\n".join(lines)


def make_category_table(analysis: dict) -> str:
    per_cat = analysis["per_category"]

    # Sort by mean_verif_value descending
    rows = sorted(per_cat.items(), key=lambda x: -x[1].get("mean_verif_value", 0))

    lines = [
        r"\begin{table}[h]",
        r"\centering",
        r"\caption{Verification Value by Task Category}",
        r"\label{tab:verification_by_category}",
        r"\begin{tabular}{lrrrrr}",
        r"\toprule",
        r"\textbf{Category} & \textbf{N} & \textbf{Helped} & \textbf{Hurt} & \textbf{Neutral/TN} & \textbf{Mean $\Delta$} \\",
        r"\midrule",
    ]

    for cat, s in rows:
        n = s["n_tasks"]
        helped = s["n_helped"]
        hurt = s["n_hurt"]
        neutral = s["n_neutral_tn"]
        delta = s["mean_verif_value"]
        delta_str = f"{delta:+.3f}"
        lines.append(f"{cat} & {n} & {helped} & {hurt} & {neutral} & {delta_str} \\\\")

    lines += [
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table}",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 8. Print summary
# ---------------------------------------------------------------------------

def print_summary(analysis: dict) -> None:
    s = analysis["summary"]
    print("\n" + "=" * 70)
    print("VERIFICATION DEEP DIVE — SUMMARY")
    print("=" * 70)
    print(f"Tasks analyzed:        {s['total_tasks_analyzed']}")
    print(f"Total runs loaded:     {s['total_runs_loaded']}")
    print()
    print(f"Mean score (full):      {s['mean_full_score']:.3f}")
    print(f"Mean score (no_verify): {s['mean_no_verify_score']:.3f}")
    print(f"Mean score (oracle):    {s['mean_oracle_score']:.3f}")
    print()
    print(f"Mean verification value (full - no_verify): {s['mean_verification_value']:+.3f}")
    print(f"  -> {'POSITIVE: verifier adds value on average' if s['mean_verification_value'] > 0 else 'NEGATIVE: no-verify beats full on average'}")
    print()
    print(f"Heuristic test — if we just skip verification:")
    print(f"  no_verify vs full gain: {s['heuristic_gain_no_verify_vs_full']:+.3f}")
    print(f"  -> {'Skipping verification IMPROVES score' if s['heuristic_gain_no_verify_vs_full'] > 0 else 'Skipping verification hurts score'}")
    print()
    print("FAILURE MODE TAXONOMY (per-task):")
    taxonomy = s["taxonomy_per_task"]
    total = s["total_tasks_analyzed"]
    for key, label in [
        ("true_positive",        "True Positive"),
        ("true_negative",        "True Negative"),
        ("false_rejection",      "False Rejection"),
        ("hallucinated_req",     "Hallucinated Requirements"),
        ("verification_neutral", "Verification Neutral"),
        ("insufficient_data",    "Insufficient Data"),
    ]:
        n = taxonomy.get(key, 0)
        print(f"  {label:<30} {n:4d}  ({100*n/total:.1f}%)")
    print()
    print(f"Tasks where verification HELPED: {s['n_tasks_verification_helped']}")
    print(f"Tasks where verification HURT:   {s['n_tasks_verification_hurt']}")
    print(f"Tasks neutral/approved:          {s['n_tasks_neutral_or_tn']}")
    if s["mean_score_drop_false_rejections"] > 0:
        print(f"Mean score drop when verification hurts: {s['mean_score_drop_false_rejections']:.3f}")
    print(f"Fraction of tasks where skipping verification would win: {s.get('frac_tasks_nv_better', 0):.1%}")
    print()
    print("TOP FALSE REJECTION TASKS (worst score drop first):")
    for item in analysis["false_rejection_details"][:10]:
        print(f"  {item['task_id']:<35} drop={item['mean_score_drop']:.3f}  [{item['category']}]")
    print()
    print("PER-CATEGORY VERIFICATION VALUE:")
    cats = sorted(analysis["per_category"].items(),
                  key=lambda x: -x[1].get("mean_verif_value", 0))
    print(f"  {'Category':<25} {'N':>4} {'Helped':>7} {'Hurt':>5} {'Mean Δ':>8}")
    print(f"  {'-'*54}")
    for cat, s_cat in cats:
        print(f"  {cat:<25} {s_cat['n_tasks']:>4} {s_cat['n_helped']:>7} "
              f"{s_cat['n_hurt']:>5} {s_cat['mean_verif_value']:>+8.3f}")
    print()
    print("PER-DIFFICULTY-QUINTILE VERIFICATION VALUE:")
    quintile_order = ["Q1_hardest", "Q2_hard", "Q3_medium", "Q4_easy", "Q5_easiest"]
    per_q = analysis["per_difficulty_quintile"]
    for q in quintile_order:
        if q in per_q:
            sq = per_q[q]
            print(f"  {q}: N={sq['n_tasks']:3d}  mean_delta={sq['mean_verif_value']:+.3f}")
    print()
    print("HYPOTHESIS CHECK:")
    adv_cats = {"Adversarial", "Cryptographic", "Distributed", "Cross-System", "Security"}
    adv_vals = [v["mean_verif_value"] for k, v in analysis["per_category"].items()
                if k in adv_cats]
    simple_cats = {"Software", "Code Review", "Data", "Data Science"}
    simple_vals = [v["mean_verif_value"] for k, v in analysis["per_category"].items()
                   if k in simple_cats]
    if adv_vals:
        print(f"  Adversarial/complex categories avg verif value: {sum(adv_vals)/len(adv_vals):+.3f}")
    if simple_vals:
        print(f"  Simple coding categories avg verif value:        {sum(simple_vals)/len(simple_vals):+.3f}")
    print("=" * 70)


# ---------------------------------------------------------------------------
# 9. Entrypoint
# ---------------------------------------------------------------------------

def main() -> None:
    analysis = run_analysis()

    # Write JSON
    out_json = os.path.join(PAPER_DIR, "verification_deep_dive.json")
    with open(out_json, "w") as f:
        json.dump(analysis, f, indent=2, default=str)
    print(f"\nWrote: {out_json}")

    # Write taxonomy LaTeX table
    taxonomy_tex = make_taxonomy_table(analysis)
    out_taxonomy = os.path.join(PAPER_DIR, "table_verification_taxonomy.tex")
    with open(out_taxonomy, "w") as f:
        f.write(taxonomy_tex + "\n")
    print(f"Wrote: {out_taxonomy}")

    # Write per-category LaTeX table
    cat_tex = make_category_table(analysis)
    out_cat = os.path.join(PAPER_DIR, "table_verification_by_category.tex")
    with open(out_cat, "w") as f:
        f.write(cat_tex + "\n")
    print(f"Wrote: {out_cat}")

    print_summary(analysis)


if __name__ == "__main__":
    main()
