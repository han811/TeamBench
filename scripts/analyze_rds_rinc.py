#!/usr/bin/env python3
"""Analyze RDS/RINC ablation results by task archetype.

Reads the ablation JSON produced by run_rds_rinc_ablation.py and computes:
  - Per-archetype: mean TNI, team uplift, planning value, verification value
  - One-way ANOVA: does archetype predict TNI?
  - LaTeX table: shared/paper/table_archetype_tni.tex
  - JSON summary: shared/paper/archetype_analysis.json

Archetype classification:
  RDS1-RDS10  -> open_ended
  RDS11-RDS18 -> adversarial
  RDS19-RDS24 -> discovery
  RDS25-RDS30 -> synthesis
  RINC*       -> incident

Usage:
    python scripts/analyze_rds_rinc.py
    python scripts/analyze_rds_rinc.py --input shared/ablation_results/rds_rinc_ablation_gemini3flashpreview_seed0.json
    python scripts/analyze_rds_rinc.py --latex shared/paper/table_archetype_tni.tex
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from collections import defaultdict
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ARCHETYPE_ORDER = ["adversarial", "synthesis", "discovery", "open_ended", "incident"]
ARCHETYPE_LABELS = {
    "adversarial": "Adversarial",
    "synthesis": "Synthesis",
    "discovery": "Discovery",
    "open_ended": "Open-ended",
    "incident": "Incident",
}

EPS = 1e-6


# ---------------------------------------------------------------------------
# Archetype classification (mirrors run_rds_rinc_ablation.py)
# ---------------------------------------------------------------------------

def classify_archetype(task_id: str) -> str:
    m = re.match(r"^(RDS|RINC)(\d+)", task_id)
    if m is None:
        return "unknown"
    prefix = m.group(1)
    num = int(m.group(2))
    if prefix == "RINC":
        return "incident"
    if 1 <= num <= 10:
        return "open_ended"
    if 11 <= num <= 18:
        return "adversarial"
    if 19 <= num <= 24:
        return "discovery"
    if 25 <= num <= 30:
        return "synthesis"
    return "open_ended"


# ---------------------------------------------------------------------------
# Statistics helpers
# ---------------------------------------------------------------------------

def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _variance(xs: list[float]) -> float:
    if len(xs) < 2:
        return 0.0
    m = _mean(xs)
    return sum((x - m) ** 2 for x in xs) / (len(xs) - 1)


def _regularised_incomplete_beta(
    x: float, a: float, b: float, max_iter: int = 200
) -> float:
    """Approximate I_x(a, b) using the continued fraction method (Lentz)."""
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    if x > (a + 1) / (a + b + 2):
        return 1.0 - _regularised_incomplete_beta(1 - x, b, a, max_iter)

    lbeta = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
    front = math.exp(math.log(x) * a + math.log(1 - x) * b - lbeta) / a

    tiny = 1e-30
    f = tiny
    C = f
    D = 0.0
    for m_iter in range(0, max_iter):
        for n_iter in range(2):
            if n_iter == 0:
                d = 1.0 if m_iter == 0 else (
                    -(a + m_iter - 1) * (a + b + m_iter - 1) * x
                    / ((a + 2 * m_iter - 1) * (a + 2 * m_iter))
                )
            else:
                d = (
                    m_iter * (b - m_iter) * x
                    / ((a + 2 * m_iter - 1) * (a + 2 * m_iter))
                )
            D = 1 + d * D
            if abs(D) < tiny:
                D = tiny
            C = 1 + d / C
            if abs(C) < tiny:
                C = tiny
            D = 1 / D
            delta = C * D
            f *= delta
            if abs(delta - 1) < 1e-10:
                return front * f
    return front * f


def _f_pvalue(F: float, df1: int, df2: int) -> float:
    """P(X >= F) for X ~ F(df1, df2)."""
    x = df1 * F / (df1 * F + df2)
    return 1.0 - _regularised_incomplete_beta(x, df1 / 2, df2 / 2)


def one_way_anova(groups: dict[str, list[float]]) -> dict[str, Any]:
    """One-way ANOVA across groups. Returns F, p_value, eta_squared."""
    all_vals: list[float] = []
    for v in groups.values():
        all_vals.extend(v)
    if len(all_vals) < 2:
        return {"F": None, "p_value": None, "eta_squared": None,
                "df_between": 0, "df_within": 0}

    grand_mean = _mean(all_vals)
    k = sum(1 for v in groups.values() if v)
    n_total = len(all_vals)

    ss_between = sum(
        len(v) * (_mean(v) - grand_mean) ** 2 for v in groups.values() if v
    )
    ss_within = sum(
        sum((x - _mean(v)) ** 2 for x in v) for v in groups.values() if v
    )
    df_between = k - 1
    df_within = n_total - k

    if df_between <= 0 or df_within <= 0 or ss_within < EPS:
        return {
            "F": None, "p_value": None, "eta_squared": None,
            "df_between": df_between, "df_within": df_within,
            "ss_between": ss_between, "ss_within": ss_within,
        }

    ms_between = ss_between / df_between
    ms_within = ss_within / df_within
    F = ms_between / ms_within
    eta_sq = ss_between / (ss_between + ss_within)

    try:
        p_value = _f_pvalue(F, df_between, df_within)
    except Exception:
        p_value = None

    return {
        "F": round(F, 4),
        "p_value": round(p_value, 6) if p_value is not None else None,
        "df_between": df_between,
        "df_within": df_within,
        "ss_between": round(ss_between, 6),
        "ss_within": round(ss_within, 6),
        "eta_squared": round(eta_sq, 4),
        "group_means": {k: round(_mean(v), 4) for k, v in groups.items() if v},
        "group_sizes": {k: len(v) for k, v in groups.items() if v},
    }


# ---------------------------------------------------------------------------
# Per-task and per-archetype metric computation
# ---------------------------------------------------------------------------

def compute_per_task_metrics(runs: list[dict]) -> dict[str, dict]:
    """Compute per-task scores across conditions."""
    task_cond: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for run in runs:
        task_id = run.get("task_id", "")
        cond = run.get("condition", "")
        ps = run.get("partial_score")
        if ps is None:
            ps = 1.0 if run.get("pass") else 0.0
        task_cond[task_id][cond].append(float(ps))

    results: dict[str, dict] = {}
    for task_id, cond_scores in task_cond.items():
        s_oracle = _mean(cond_scores.get("oracle", []))
        s_restricted = _mean(cond_scores.get("restricted", []))
        s_full = _mean(cond_scores.get("full", []))
        s_no_plan = _mean(cond_scores.get("team_no_plan", []))
        s_no_verify = _mean(cond_scores.get("team_no_verify", []))

        tni = (s_full - s_restricted) / max(EPS, s_oracle - s_restricted)
        results[task_id] = {
            "archetype": classify_archetype(task_id),
            "oracle": round(s_oracle, 4),
            "restricted": round(s_restricted, 4),
            "full": round(s_full, 4),
            "team_no_plan": round(s_no_plan, 4),
            "team_no_verify": round(s_no_verify, 4),
            "tni": round(tni, 4),
            "team_uplift": round(s_full - s_oracle, 4),
            "planning_value": round(s_full - s_no_plan, 4),
            "verification_value": round(s_full - s_no_verify, 4),
            "n_runs": {c: len(v) for c, v in cond_scores.items()},
        }
    return results


def compute_per_archetype_metrics(per_task: dict[str, dict]) -> dict[str, dict]:
    """Aggregate per-task metrics into per-archetype summaries."""
    arch_tasks: dict[str, list[dict]] = defaultdict(list)
    for task_id, m in per_task.items():
        arch_tasks[m["archetype"]].append(m)

    results: dict[str, dict] = {}
    for arch, tasks in arch_tasks.items():
        tni_vals = [t["tni"] for t in tasks]
        uplift_vals = [t["team_uplift"] for t in tasks]
        plan_vals = [t["planning_value"] for t in tasks]
        ver_vals = [t["verification_value"] for t in tasks]

        results[arch] = {
            "n_tasks": len(tasks),
            "mean_tni": round(_mean(tni_vals), 4),
            "std_tni": round(_variance(tni_vals) ** 0.5, 4) if len(tni_vals) > 1 else 0.0,
            "mean_team_uplift": round(_mean(uplift_vals), 4),
            "mean_planning_value": round(_mean(plan_vals), 4),
            "mean_verification_value": round(_mean(ver_vals), 4),
            "mean_oracle": round(_mean([t["oracle"] for t in tasks]), 4),
            "mean_restricted": round(_mean([t["restricted"] for t in tasks]), 4),
            "mean_full": round(_mean([t["full"] for t in tasks]), 4),
            "tni_values": tni_vals,  # kept for ANOVA
        }
    return results


def run_archetype_anova(per_archetype: dict[str, dict]) -> dict[str, Any]:
    """One-way ANOVA: does archetype predict TNI?"""
    groups = {
        arch: data["tni_values"]
        for arch, data in per_archetype.items()
        if data["tni_values"]
    }
    return one_way_anova(groups)


def check_hypothesis(per_archetype: dict[str, dict]) -> dict[str, Any]:
    """Test: adversarial TNI > all other archetypes."""
    adv = per_archetype.get("adversarial", {})
    adv_tni = adv.get("mean_tni")
    if adv_tni is None:
        return {"supported": None, "reason": "No adversarial results"}

    others = {
        k: v["mean_tni"]
        for k, v in per_archetype.items()
        if k != "adversarial" and k != "unknown" and v.get("mean_tni") is not None
    }
    if not others:
        return {"supported": None, "reason": "No other archetypes to compare"}

    max_other = max(others, key=lambda k: others[k])
    supported = adv_tni > others[max_other]
    return {
        "supported": supported,
        "adversarial_tni": adv_tni,
        "max_other_archetype": max_other,
        "max_other_tni": others[max_other],
        "all_other_tnis": others,
        "reason": (
            f"adversarial TNI={adv_tni:.4f} {'>' if supported else '<='} "
            f"{max_other} TNI={others[max_other]:.4f}"
        ),
    }


# ---------------------------------------------------------------------------
# LaTeX table generation
# ---------------------------------------------------------------------------

def generate_latex_table(
    per_archetype: dict[str, dict],
    anova: dict[str, Any],
    hypothesis: dict[str, Any],
    output_path: str,
) -> None:
    lines: list[str] = []
    lines.append(r"% Auto-generated by scripts/analyze_rds_rinc.py")
    lines.append(r"\begin{table}[t]")
    lines.append(r"\centering")
    lines.append(r"\small")

    # Caption
    hyp_note = (
        r"Hypothesis (adversarial TNI $>$ other archetypes): \textbf{supported}."
        if hypothesis.get("supported")
        else r"Hypothesis (adversarial TNI $>$ other archetypes): not supported."
    )
    if hypothesis.get("supported") is None:
        hyp_note = r"Insufficient data to test hypothesis."

    F_str = f"{anova['F']:.2f}" if anova.get("F") is not None else "---"
    p_str = f"{anova['p_value']:.4f}" if anova.get("p_value") is not None else "---"
    eta_str = f"{anova['eta_squared']:.3f}" if anova.get("eta_squared") is not None else "---"
    anova_note = (
        f"One-way ANOVA (archetype predicts TNI): "
        f"$F={F_str}$, $p={p_str}$, $\\eta^2={eta_str}$."
    )

    lines.append(
        r"\caption{Per-archetype teamwork necessity index (TNI) for RDS/RINC tasks. "
        + anova_note + " " + hyp_note + r"}"
    )
    lines.append(r"\label{tab:archetype_tni}")
    lines.append(r"\begin{tabular}{lrrrrrr}")
    lines.append(r"\toprule")
    lines.append(
        r"Archetype & $N$ & Oracle & Restricted & Full & TNI & Team Uplift \\"
    )
    lines.append(r"\midrule")

    for arch in ARCHETYPE_ORDER:
        if arch not in per_archetype:
            continue
        r = per_archetype[arch]
        label = ARCHETYPE_LABELS.get(arch, arch)
        # Bold highest TNI
        tni_str = f"{r['mean_tni']:.3f}"
        if hypothesis.get("supported") and arch == "adversarial":
            tni_str = r"\textbf{" + tni_str + r"}"
        lines.append(
            f"  {label} & {r['n_tasks']} & "
            f"{r['mean_oracle']:.3f} & {r['mean_restricted']:.3f} & "
            f"{r['mean_full']:.3f} & {tni_str} & "
            f"{r['mean_team_uplift']:+.3f} \\\\"
        )

    lines.append(r"\midrule")
    # Overall row
    all_tasks_n = sum(v["n_tasks"] for v in per_archetype.values() if v.get("n_tasks"))
    all_tni = [v["mean_tni"] for v in per_archetype.values() if v.get("mean_tni") is not None]
    all_oracle = [v["mean_oracle"] for v in per_archetype.values() if v.get("mean_oracle") is not None]
    all_restr = [v["mean_restricted"] for v in per_archetype.values() if v.get("mean_restricted") is not None]
    all_full = [v["mean_full"] for v in per_archetype.values() if v.get("mean_full") is not None]
    all_uplift = [v["mean_team_uplift"] for v in per_archetype.values() if v.get("mean_team_uplift") is not None]

    lines.append(
        f"  \\textit{{Overall}} & {all_tasks_n} & "
        f"{_mean(all_oracle):.3f} & {_mean(all_restr):.3f} & "
        f"{_mean(all_full):.3f} & {_mean(all_tni):.3f} & "
        f"{_mean(all_uplift):+.3f} \\\\"
    )

    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}")
    lines.append(r"\end{table}")

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"  LaTeX table -> {output_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(
        description="Analyze RDS/RINC archetype ablation results",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument(
        "--input",
        default=None,
        help=(
            "Input ablation JSON (default: auto-detect latest "
            "rds_rinc_ablation_*.json in shared/ablation_results/)"
        ),
    )
    ap.add_argument(
        "--latex",
        default=os.path.join(REPO_ROOT, "shared", "paper", "table_archetype_tni.tex"),
        help="Output LaTeX table path",
    )
    ap.add_argument(
        "--output",
        default=os.path.join(REPO_ROOT, "shared", "paper", "archetype_analysis.json"),
        help="Output analysis JSON path",
    )
    args = ap.parse_args()

    # Auto-detect input if not specified
    if args.input is None:
        results_dir = os.path.join(REPO_ROOT, "shared", "ablation_results")
        candidates = sorted(
            f for f in os.listdir(results_dir)
            if f.startswith("rds_rinc_ablation_") and f.endswith(".json")
        )
        if not candidates:
            print(
                "ERROR: No rds_rinc_ablation_*.json found in shared/ablation_results/.\n"
                "Run scripts/run_rds_rinc_ablation.py first.",
                file=sys.stderr,
            )
            sys.exit(1)
        args.input = os.path.join(results_dir, candidates[-1])
        print(f"Auto-detected input: {args.input}")

    input_path = os.path.abspath(args.input)
    if not os.path.isfile(input_path):
        print(f"ERROR: Input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Loading results from {input_path} ...")
    with open(input_path, encoding="utf-8") as f:
        data = json.load(f)

    runs = data.get("runs", [])
    print(f"  {len(runs)} runs loaded")

    if not runs:
        print("ERROR: No runs found in input file.", file=sys.stderr)
        sys.exit(1)

    # Compute metrics
    print("Computing per-task metrics ...")
    per_task = compute_per_task_metrics(runs)
    print(f"  {len(per_task)} tasks")

    print("Computing per-archetype metrics ...")
    per_archetype = compute_per_archetype_metrics(per_task)

    # Strip tni_values from JSON output (kept internally for ANOVA only)
    per_archetype_clean = {
        arch: {k: v for k, v in data.items() if k != "tni_values"}
        for arch, data in per_archetype.items()
    }

    print("Running one-way ANOVA (archetype -> TNI) ...")
    anova = run_archetype_anova(per_archetype)

    print("Testing hypothesis ...")
    hypothesis = check_hypothesis(per_archetype)

    # -----------------------------------------------------------------------
    # Print summary
    # -----------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("PER-ARCHETYPE SUMMARY")
    print("=" * 70)
    print(f"  {'Archetype':<14} {'N':>4}  {'Oracle':>7}  {'Full':>7}  "
          f"{'TNI':>7}  {'Uplift':>8}  {'PlanVal':>8}  {'VerVal':>8}")
    print("  " + "-" * 66)

    for arch in ARCHETYPE_ORDER:
        if arch not in per_archetype:
            continue
        r = per_archetype[arch]
        marker = " *" if arch == "adversarial" and hypothesis.get("supported") else "  "
        print(
            f"  {arch:<14}{marker} {r['n_tasks']:>4}  "
            f"{r['mean_oracle']:>7.3f}  {r['mean_full']:>7.3f}  "
            f"{r['mean_tni']:>7.4f}  {r['mean_team_uplift']:>+8.3f}  "
            f"{r['mean_planning_value']:>+8.3f}  {r['mean_verification_value']:>+8.3f}"
        )
    print("=" * 70)

    print(f"\nOne-way ANOVA (archetype predicts TNI):")
    F_str = f"{anova['F']:.4f}" if anova.get("F") is not None else "N/A"
    p_str = f"{anova['p_value']:.6f}" if anova.get("p_value") is not None else "N/A"
    eta_str = f"{anova['eta_squared']:.4f}" if anova.get("eta_squared") is not None else "N/A"
    print(f"  F={F_str}, p={p_str}, eta2={eta_str}")
    if anova.get("p_value") is not None:
        sig = "significant" if anova["p_value"] < 0.05 else "not significant"
        print(f"  -> Archetype effect is {sig} (p<0.05 threshold)")

    print(f"\nHypothesis (adversarial TNI > others): {hypothesis['reason']}")
    if hypothesis.get("supported"):
        print("  -> HYPOTHESIS SUPPORTED")
    elif hypothesis.get("supported") is False:
        print("  -> HYPOTHESIS NOT SUPPORTED")
    else:
        print("  -> INSUFFICIENT DATA")

    # -----------------------------------------------------------------------
    # Write outputs
    # -----------------------------------------------------------------------
    print("\nGenerating outputs ...")
    generate_latex_table(per_archetype, anova, hypothesis, args.latex)

    analysis_out = {
        "source": input_path,
        "model": data.get("model", "unknown"),
        "seeds": data.get("seeds", []),
        "n_runs": len(runs),
        "n_tasks": len(per_task),
        "per_archetype": per_archetype_clean,
        "per_task": per_task,
        "anova": anova,
        "hypothesis": hypothesis,
        "archetype_order_by_tni": sorted(
            [a for a in per_archetype if a != "unknown"],
            key=lambda a: per_archetype[a].get("mean_tni", 0),
            reverse=True,
        ),
    }

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(analysis_out, f, indent=2)
    print(f"  Analysis JSON -> {args.output}")

    print(f"\nDone.")


if __name__ == "__main__":
    main()
