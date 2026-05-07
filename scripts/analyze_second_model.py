#!/usr/bin/env python3
"""Validate TeamBench team benefits on a second model (GPT-5-Nano/Mini) vs
the primary reference model (Gemini 3 Flash).

Loads ablation results from both model families, computes per-task Spearman
rank correlations, shows which tasks consistently benefit from teamwork, and
generates a LaTeX comparison table for the paper.

Outputs:
  shared/paper/table_second_model_validation.tex  — LaTeX comparison table
  shared/paper/second_model_stats.json            — full per-task/model stats

Usage:
    # Auto-discover all ablation JSONs (uses model field inside each file):
    python scripts/analyze_second_model.py --dir shared/ablation_results

    # Explicit files:
    python scripts/analyze_second_model.py \\
        --gemini  shared/ablation_results/full_ablation_g3flash_seed0.json \\
        --openai  shared/ablation_results/full_ablation_gpt5nano_seed0.json

    # Custom output dir:
    python scripts/analyze_second_model.py --dir shared/ablation_results \\
        --output-dir shared/paper
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import os
import sys
from collections import defaultdict
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from harness.compute_tni import TaskMetrics
from harness.paper_tables import CATEGORY_MAP, runs_to_task_metrics


# ---------------------------------------------------------------------------
# Helpers shared with cross_model_analysis (inlined to keep script standalone)
# ---------------------------------------------------------------------------

def _task_prefix(task_id: str) -> str:
    first_part = task_id.split("_")[0] if "_" in task_id else task_id
    prefix = ""
    for ch in first_part:
        if ch.isalpha():
            prefix += ch
        else:
            break
    return prefix.upper()


def _task_category(task_id: str) -> str:
    return CATEGORY_MAP.get(_task_prefix(task_id), _task_prefix(task_id))


def spearman_rank_correlation(x: list[float], y: list[float]) -> float:
    """Pure-Python Spearman rho with average-rank tie handling."""
    n = len(x)
    if n < 3:
        return float("nan")

    def _ranks(vals: list[float]) -> list[float]:
        indexed = sorted(enumerate(vals), key=lambda kv: kv[1])
        ranks = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j < n - 1 and indexed[j + 1][1] == indexed[i][1]:
                j += 1
            avg_rank = (i + j) / 2.0 + 1.0
            for k in range(i, j + 1):
                ranks[indexed[k][0]] = avg_rank
            i = j + 1
        return ranks

    rx, ry = _ranks(x), _ranks(y)
    mrx = sum(rx) / n
    mry = sum(ry) / n
    cov = sum((rx[i] - mrx) * (ry[i] - mry) for i in range(n))
    std_rx = math.sqrt(sum((r - mrx) ** 2 for r in rx))
    std_ry = math.sqrt(sum((r - mry) ** 2 for r in ry))
    denom = std_rx * std_ry
    return float("nan") if denom < 1e-9 else cov / denom


def _tni_val(m: TaskMetrics) -> Optional[float]:
    if math.isnan(m.tni) or abs(m.necessity_gap) <= 0.05:
        return None
    return m.tni


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def _is_gemini(model: str) -> bool:
    return "gemini" in model.lower() or "flash" in model.lower() or "pro" in model.lower()


def _is_openai(model: str) -> bool:
    return "gpt" in model.lower() or "openai" in model.lower()


def load_runs_from_file(path: str) -> tuple[str, list[dict]]:
    """Load runs from one ablation JSON; return (model_name, [runs])."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    model = data.get("model", os.path.basename(path).replace(".json", ""))
    return model, data.get("runs", [])


def load_model_group(paths: list[str]) -> tuple[str, list[dict]]:
    """Merge runs from multiple files that belong to the same model family."""
    all_runs: list[dict] = []
    model_name = ""
    seen: set[tuple] = set()
    for p in paths:
        mn, runs = load_runs_from_file(p)
        if not model_name:
            model_name = mn
        for r in runs:
            key = (r.get("task_id", ""), r.get("condition", ""), r.get("seed", 0))
            if key not in seen:
                seen.add(key)
                all_runs.append(r)
    return model_name, all_runs


def task_metrics_for_runs(runs: list[dict]) -> dict[str, TaskMetrics]:
    metrics_list = runs_to_task_metrics(runs)
    return {m.task_id: m for m in metrics_list}


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def compute_stats(
    model_a_name: str,
    metrics_a: dict[str, TaskMetrics],
    model_b_name: str,
    metrics_b: dict[str, TaskMetrics],
) -> dict:
    """Compute full comparison stats between two models."""
    all_tasks = sorted(set(metrics_a) | set(metrics_b))
    shared_tasks = [t for t in all_tasks if t in metrics_a and t in metrics_b]

    # Per-model aggregates
    def _agg(name: str, metrics: dict[str, TaskMetrics]) -> dict:
        ms = list(metrics.values())
        if not ms:
            return {"task_count": 0}
        valid_tni = [_tni_val(m) for m in ms if _tni_val(m) is not None]
        team_wins = sum(1 for m in ms if m.team_uplift > 0.01)
        return {
            "model": name,
            "task_count": len(ms),
            "avg_oracle": round(sum(m.oracle_partial for m in ms) / len(ms), 4),
            "avg_restricted": round(sum(m.restricted_partial for m in ms) / len(ms), 4),
            "avg_team": round(sum(m.team_partial for m in ms) / len(ms), 4),
            "avg_uplift": round(sum(m.team_uplift for m in ms) / len(ms), 4),
            "avg_tni": round(sum(valid_tni) / len(valid_tni), 4) if valid_tni else None,
            "valid_tni_count": len(valid_tni),
            "team_helps_count": team_wins,
            "team_helps_pct": round(team_wins / len(ms), 4),
        }

    agg_a = _agg(model_a_name, metrics_a)
    agg_b = _agg(model_b_name, metrics_b)

    # Spearman correlations on shared tasks
    correlations: dict = {}
    if len(shared_tasks) >= 3:
        tni_a = [_tni_val(metrics_a[t]) or 0.0 for t in shared_tasks]
        tni_b = [_tni_val(metrics_b[t]) or 0.0 for t in shared_tasks]
        uplift_a = [metrics_a[t].team_uplift for t in shared_tasks]
        uplift_b = [metrics_b[t].team_uplift for t in shared_tasks]
        correlations = {
            "n_shared_tasks": len(shared_tasks),
            "spearman_tni": round(spearman_rank_correlation(tni_a, tni_b), 4),
            "spearman_uplift": round(spearman_rank_correlation(uplift_a, uplift_b), 4),
        }
    else:
        correlations = {
            "n_shared_tasks": len(shared_tasks),
            "spearman_tni": None,
            "spearman_uplift": None,
            "note": "Insufficient shared tasks for correlation",
        }

    # Tasks where both models agree on direction
    consistent_helps = [
        t for t in shared_tasks
        if metrics_a[t].team_uplift > 0.01 and metrics_b[t].team_uplift > 0.01
    ]
    consistent_hurts = [
        t for t in shared_tasks
        if metrics_a[t].team_uplift < -0.01 and metrics_b[t].team_uplift < -0.01
    ]
    disagreements = [
        t for t in shared_tasks
        if (metrics_a[t].team_uplift > 0.01 and metrics_b[t].team_uplift < -0.01)
        or (metrics_a[t].team_uplift < -0.01 and metrics_b[t].team_uplift > 0.01)
    ]

    # Per-task detail
    per_task = []
    for t in all_tasks:
        ma = metrics_a.get(t)
        mb = metrics_b.get(t)
        entry: dict = {
            "task_id": t,
            "category": _task_category(t),
            model_a_name: None,
            model_b_name: None,
        }
        for label, m in [(model_a_name, ma), (model_b_name, mb)]:
            if m is not None:
                tni_v = _tni_val(m)
                entry[label] = {
                    "oracle": round(m.oracle_partial, 4),
                    "restricted": round(m.restricted_partial, 4),
                    "team": round(m.team_partial, 4),
                    "uplift": round(m.team_uplift, 4),
                    "tni": round(tni_v, 4) if tni_v is not None else None,
                    "classification": m.classification,
                }
        per_task.append(entry)

    return {
        "model_a": model_a_name,
        "model_b": model_b_name,
        "total_tasks": len(all_tasks),
        "shared_tasks": len(shared_tasks),
        "per_model": {model_a_name: agg_a, model_b_name: agg_b},
        "correlations": correlations,
        "consistent_team_helps": consistent_helps,
        "consistent_team_hurts": consistent_hurts,
        "disagreements": disagreements,
        "per_task": per_task,
    }


# ---------------------------------------------------------------------------
# LaTeX table
# ---------------------------------------------------------------------------

def generate_latex_table(stats: dict) -> str:
    model_a = stats["model_a"]
    model_b = stats["model_b"]

    # Shorten model names for column headers
    def _short(name: str) -> str:
        name = name.replace("gemini-", "G").replace("flash", "Fl").replace("preview", "")
        name = name.replace("gpt-5-nano", "GPT-5-nano").replace("gpt-5-mini", "GPT-5-mini")
        name = name.replace("gpt-5", "GPT-5").replace("-preview", "")
        return name.strip("-").strip()

    short_a = _short(model_a)
    short_b = _short(model_b)

    per_task_map: dict[str, dict] = {}
    for entry in stats["per_task"]:
        per_task_map[entry["task_id"]] = entry

    all_tasks = sorted(per_task_map)

    lines = [
        "% Auto-generated by scripts/analyze_second_model.py",
        r"\begin{table*}[t]",
        r"\centering",
        r"\caption{Second-model validation. "
        r"We replicate the full ablation on a second model family to confirm "
        r"that team benefits are not an artefact of the primary model. "
        r"Oracle / Team columns show partial scores; TNI is shown where the "
        r"necessity gap $>0.05$. "
        r"$\uparrow$ = team helps both models; $\downarrow$ = team hurts both; "
        r"$\leftrightarrow$ = models disagree.}",
        r"\label{tab:second-model}",
        r"\scriptsize",
        r"\begin{tabular}{llcccccccc}",
        r"\toprule",
        r"\multicolumn{2}{l}{} "
        r"& \multicolumn{3}{c}{" + short_a + r"} "
        r"& \multicolumn{3}{c}{" + short_b + r"} "
        r"& \multicolumn{2}{c}{Agreement} \\",
        r"\cmidrule(lr){3-5}\cmidrule(lr){6-8}\cmidrule(lr){9-10}",
        r"Task & Cat "
        r"& Oracle & Team & TNI "
        r"& Oracle & Team & TNI "
        r"& Dir. & $\Delta$Uplift \\",
        r"\midrule",
    ]

    consistent_helps = set(stats["consistent_team_helps"])
    consistent_hurts = set(stats["consistent_team_hurts"])

    avgs: dict[str, list] = defaultdict(list)

    for task_id in all_tasks:
        entry = per_task_map[task_id]
        cat = entry["category"]
        task_short = task_id.replace("_", r"\_")

        ma = entry.get(model_a)
        mb = entry.get(model_b)

        def _fmt(m: Optional[dict], key: str) -> str:
            if m is None:
                return "--"
            v = m.get(key)
            return f"{v:.2f}" if v is not None else "--"

        tni_a_str = _fmt(ma, "tni")
        tni_b_str = _fmt(mb, "tni")

        # Collect averages
        for label, m in [(model_a, ma), (model_b, mb)]:
            if m:
                avgs[f"{label}_oracle"].append(m["oracle"])
                avgs[f"{label}_team"].append(m["team"])
                if m.get("tni") is not None:
                    avgs[f"{label}_tni"].append(m["tni"])

        # Direction marker
        if task_id in consistent_helps:
            direction = r"$\uparrow$"
        elif task_id in consistent_hurts:
            direction = r"$\downarrow$"
        elif ma and mb:
            direction = r"$\leftrightarrow$"
        else:
            direction = "--"

        # Delta uplift between models (B - A)
        if ma and mb:
            delta = mb["uplift"] - ma["uplift"]
            delta_str = f"{delta:+.2f}"
        else:
            delta_str = "--"

        oracle_a = _fmt(ma, "oracle")
        team_a = _fmt(ma, "team")
        oracle_b = _fmt(mb, "oracle")
        team_b = _fmt(mb, "team")

        lines.append(
            f"{task_short} & {cat} "
            f"& {oracle_a} & {team_a} & {tni_a_str} "
            f"& {oracle_b} & {team_b} & {tni_b_str} "
            f"& {direction} & {delta_str} \\\\"
        )

    # Average row
    def _avg_str(key: str) -> str:
        vals = avgs.get(key, [])
        return f"{sum(vals)/len(vals):.2f}" if vals else "--"

    lines.append(r"\midrule")
    lines.append(
        r"\textbf{Average} & "
        + f"({len(all_tasks)} tasks) "
        + f"& {_avg_str(model_a + '_oracle')} "
        + f"& {_avg_str(model_a + '_team')} "
        + f"& {_avg_str(model_a + '_tni')} "
        + f"& {_avg_str(model_b + '_oracle')} "
        + f"& {_avg_str(model_b + '_team')} "
        + f"& {_avg_str(model_b + '_tni')} "
        + r"& -- & -- \\"
    )

    lines.extend([
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table*}",
    ])
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Console summary
# ---------------------------------------------------------------------------

def print_summary(stats: dict) -> None:
    model_a = stats["model_a"]
    model_b = stats["model_b"]

    print("\n" + "=" * 65)
    print("Second-Model Validation Summary")
    print("=" * 65)
    print(f"  Primary model:   {model_a}")
    print(f"  Secondary model: {model_b}")
    print(f"  Total tasks: {stats['total_tasks']} "
          f"(shared: {stats['shared_tasks']})")
    print()

    for label in [model_a, model_b]:
        s = stats["per_model"].get(label, {})
        if not s.get("task_count"):
            print(f"  {label}: no data")
            continue
        tni_s = f"{s['avg_tni']:.3f}" if s.get("avg_tni") is not None else "N/A"
        print(f"  {label}:")
        print(f"    Tasks={s['task_count']}  "
              f"Oracle={s['avg_oracle']:.3f}  Team={s['avg_team']:.3f}  "
              f"Uplift={s['avg_uplift']:+.3f}")
        print(f"    Team helps: {s['team_helps_count']}/{s['task_count']} "
              f"({s['team_helps_pct']:.0%})  "
              f"Avg TNI: {tni_s} (n={s['valid_tni_count']})")

    corr = stats.get("correlations", {})
    print()
    print(f"  Spearman ρ (TNI):    "
          + (f"{corr['spearman_tni']:.3f}" if corr.get("spearman_tni") is not None else "N/A")
          + f"  (n={corr.get('n_shared_tasks', 0)} shared tasks)")
    print(f"  Spearman ρ (Uplift): "
          + (f"{corr['spearman_uplift']:.3f}" if corr.get("spearman_uplift") is not None else "N/A"))

    helps = stats.get("consistent_team_helps", [])
    hurts = stats.get("consistent_team_hurts", [])
    disagree = stats.get("disagreements", [])
    print()
    print(f"  Both models: team helps {len(helps)}, "
          f"team hurts {len(hurts)}, disagree {len(disagree)}")
    if helps:
        print(f"    Consistent helps: {', '.join(helps[:10])}"
              + ("..." if len(helps) > 10 else ""))
    if hurts:
        print(f"    Consistent hurts: {', '.join(hurts[:10])}"
              + ("..." if len(hurts) > 10 else ""))

    rho = corr.get("spearman_tni")
    if rho is not None and not math.isnan(rho):
        if rho >= 0.6:
            interp = "Strong cross-model agreement — team benefits are robust."
        elif rho >= 0.3:
            interp = "Moderate cross-model agreement — partial replication."
        else:
            interp = "Weak cross-model agreement — task difficulty varies by model."
        print(f"\n  Interpretation: {interp}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(
        description="TeamBench second-model validation analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument(
        "--gemini", nargs="+",
        metavar="FILE",
        help="Gemini ablation JSON file(s) (primary model)",
    )
    ap.add_argument(
        "--openai", nargs="+",
        metavar="FILE",
        help="OpenAI ablation JSON file(s) (secondary model)",
    )
    ap.add_argument(
        "--dir",
        help="Auto-discover all ablation JSONs in this directory and split by model family",
    )
    ap.add_argument(
        "--model-a-label",
        help="Override display name for primary (Gemini) model",
    )
    ap.add_argument(
        "--model-b-label",
        help="Override display name for secondary (OpenAI) model",
    )
    ap.add_argument(
        "--output-dir", default="shared/paper",
        help="Output directory (default: shared/paper)",
    )
    args = ap.parse_args()

    gemini_files: list[str] = []
    openai_files: list[str] = []

    if args.dir:
        d = os.path.abspath(args.dir)
        all_json = sorted(glob.glob(os.path.join(d, "*.json")))
        if not all_json:
            print(f"No JSON files found in {d}", file=sys.stderr)
            sys.exit(1)
        for path in all_json:
            try:
                with open(path) as f:
                    data = json.load(f)
                model = data.get("model", "")
            except Exception:
                continue
            if _is_gemini(model):
                gemini_files.append(path)
            elif _is_openai(model):
                openai_files.append(path)

        print(f"Auto-discovered: {len(gemini_files)} Gemini file(s), "
              f"{len(openai_files)} OpenAI file(s)")

    if args.gemini:
        gemini_files += [os.path.abspath(p) for p in args.gemini]
    if args.openai:
        openai_files += [os.path.abspath(p) for p in args.openai]

    if not gemini_files and not openai_files:
        ap.error("Provide --dir, --gemini, or --openai with result files.")

    if not gemini_files:
        print("WARNING: No Gemini files found; analysis will be single-model only.",
              file=sys.stderr)
    if not openai_files:
        print("WARNING: No OpenAI files found; analysis will be single-model only.",
              file=sys.stderr)

    # Load each model group
    model_a_name, runs_a = load_model_group(gemini_files) if gemini_files else ("gemini-unknown", [])
    model_b_name, runs_b = load_model_group(openai_files) if openai_files else ("gpt-5-nano", [])

    if args.model_a_label:
        model_a_name = args.model_a_label
    if args.model_b_label:
        model_b_name = args.model_b_label

    print(f"Model A ({model_a_name}): {len(runs_a)} runs")
    print(f"Model B ({model_b_name}): {len(runs_b)} runs")

    metrics_a = task_metrics_for_runs(runs_a) if runs_a else {}
    metrics_b = task_metrics_for_runs(runs_b) if runs_b else {}

    print(f"Tasks — A: {len(metrics_a)}, B: {len(metrics_b)}")

    stats = compute_stats(model_a_name, metrics_a, model_b_name, metrics_b)

    # Write outputs
    os.makedirs(os.path.abspath(args.output_dir), exist_ok=True)

    stats_path = os.path.join(args.output_dir, "second_model_stats.json")
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)

    table_path = os.path.join(args.output_dir, "table_second_model_validation.tex")
    table = generate_latex_table(stats)
    with open(table_path, "w", encoding="utf-8") as f:
        f.write(table)

    print(f"\nOutputs:")
    print(f"  {table_path}")
    print(f"  {stats_path}")

    print_summary(stats)


if __name__ == "__main__":
    main()
