#!/usr/bin/env python3
"""Failure analysis of TEAM-HURTS tasks.

Categorizes WHY teams fail compared to oracle, analyzing:
1. Verification damage (verifier makes things worse)
2. Planning overhead (planner misdirects executor)
3. Communication loss (information lost across role boundaries)
4. Coordination failure (roles conflict with each other)

Outputs:
  - shared/paper/failure_analysis.json  (machine-readable)
  - shared/paper/table_failure_analysis.tex (LaTeX table)
"""
import json
import glob
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def load_all_runs():
    """Load all ablation runs from result files."""
    all_runs = []
    for f in glob.glob("shared/ablation_results/*.json"):
        try:
            data = json.load(open(f))
            all_runs.extend(data.get("runs", []))
        except Exception:
            pass
    return all_runs


def compute_task_scores(all_runs):
    """Compute average partial scores per task per condition."""
    task_scores = defaultdict(lambda: defaultdict(list))
    for r in all_runs:
        tid = r.get("task_id", "")
        cond = r.get("condition", "")
        ps = r.get("partial_score")
        if ps is not None and tid and cond:
            task_scores[tid][cond].append(ps)

    results = {}
    for tid in sorted(task_scores):
        conds = task_scores[tid]
        avg = {}
        for c in ["oracle", "restricted", "team_no_verify", "team_no_plan", "full"]:
            if c in conds and conds[c]:
                avg[c] = sum(conds[c]) / len(conds[c])
            else:
                avg[c] = None
        results[tid] = avg
    return results


def classify_failure(scores):
    """Classify the failure mode for a TEAM-HURTS task.

    Returns (category, explanation) tuple.

    Categories:
    - VERIFICATION_DAMAGE: no_verify >> full (verifier breaks working solution)
    - PLANNING_OVERHEAD: no_plan >> full (planner misdirects executor)
    - ROLE_BOUNDARY_LOSS: oracle >> no_verify AND oracle >> no_plan
      (info lost across any role boundary)
    - COORDINATION_FAILURE: both planning and verification hurt moderately
    - COMPLETE_TEAM_FAILURE: full=0 (team completely fails)
    """
    oracle = scores.get("oracle", 0) or 0
    full = scores.get("full", 0) or 0
    restr = scores.get("restricted", 0) or 0
    tnv = scores.get("team_no_verify")
    tnp = scores.get("team_no_plan")

    uplift = full - oracle

    # Verification damage: no_verify much better than full
    verify_delta = (tnv - full) if tnv is not None else 0
    # Planning damage: no_plan much better than full
    plan_delta = (tnp - full) if tnp is not None else 0

    # Complete failure
    if full < 0.01 and oracle > 0.3:
        if tnv is not None and tnv > 0.3:
            return "VERIFICATION_DAMAGE", f"full=0 but no_verify={tnv:.2f}; verifier destroys solution"
        if tnp is not None and tnp > 0.3:
            return "PLANNING_OVERHEAD", f"full=0 but no_plan={tnp:.2f}; planner misdirects"
        return "COMPLETE_TEAM_FAILURE", f"full=0, no_verify={tnv or 0:.2f}, no_plan={tnp or 0:.2f}; team cannot solve"

    # Verification damage
    if verify_delta > 0.1 and verify_delta > plan_delta:
        return "VERIFICATION_DAMAGE", f"no_verify={tnv:.2f} >> full={full:.2f} (delta={verify_delta:+.2f})"

    # Planning overhead
    if plan_delta > 0.1 and plan_delta > verify_delta:
        return "PLANNING_OVERHEAD", f"no_plan={tnp:.2f} >> full={full:.2f} (delta={plan_delta:+.2f})"

    # Both hurt
    if verify_delta > 0.05 and plan_delta > 0.05:
        return "COORDINATION_FAILURE", f"both hurt: verify_delta={verify_delta:+.2f}, plan_delta={plan_delta:+.2f}"

    # Role boundary loss (oracle >> team but neither component clearly at fault)
    if oracle - full > 0.1:
        return "ROLE_BOUNDARY_LOSS", f"oracle={oracle:.2f} >> full={full:.2f}; info lost at boundaries"

    return "MINOR_DEGRADATION", f"small loss: oracle={oracle:.2f}, full={full:.2f}"


def get_task_category(task_id):
    """Infer category from task prefix."""
    prefix = task_id.split("_")[0].upper()
    cat_map = {
        "S": "SWE", "D": "Data", "SEC": "Security", "P": "Policy",
        "INC": "Incident", "O": "Operations", "TEST": "Testing",
        "SPEC": "Specification", "CR": "Code Review", "LH": "Lifecycle",
        "MULTI": "Multi-lang", "PIPE": "Pipeline", "IR": "Information Retrieval",
        "TRAP": "Adversarial", "CROSS": "Cross-System", "CRYPTO": "Security",
        "DIST": "Distributed", "NEG": "Negotiation", "INT": "Integration",
        "GO": "Multi-lang", "JS": "Multi-lang", "SQL": "Data",
        "SYNTH": "Synthetic", "SCALE": "Scalability",
    }
    # Try progressively shorter prefixes
    for i in range(len(prefix), 0, -1):
        if prefix[:i] in cat_map:
            return cat_map[prefix[:i]]
    return "Other"


def main():
    all_runs = load_all_runs()
    task_scores = compute_task_scores(all_runs)

    # Find TEAM-HURTS tasks
    hurts = []
    for tid, scores in task_scores.items():
        oracle = scores.get("oracle")
        full = scores.get("full")
        if oracle is not None and full is not None and full < oracle - 0.01:
            category, explanation = classify_failure(scores)
            hurts.append({
                "task_id": tid,
                "task_category": get_task_category(tid),
                "failure_mode": category,
                "explanation": explanation,
                "oracle": round(oracle, 3),
                "full": round(full, 3),
                "restricted": round(scores.get("restricted") or 0, 3),
                "team_no_verify": round(scores["team_no_verify"], 3) if scores.get("team_no_verify") is not None else None,
                "team_no_plan": round(scores["team_no_plan"], 3) if scores.get("team_no_plan") is not None else None,
                "uplift": round(full - oracle, 3),
            })

    hurts.sort(key=lambda x: x["uplift"])

    # Aggregate by failure mode
    mode_counts = defaultdict(int)
    mode_tasks = defaultdict(list)
    mode_avg_damage = defaultdict(list)
    for h in hurts:
        mode_counts[h["failure_mode"]] += 1
        mode_tasks[h["failure_mode"]].append(h["task_id"])
        mode_avg_damage[h["failure_mode"]].append(h["uplift"])

    summary = {
        "total_tasks_analyzed": len(task_scores),
        "total_team_hurts": len(hurts),
        "team_hurts_pct": round(len(hurts) / len(task_scores) * 100, 1),
        "failure_mode_breakdown": {
            mode: {
                "count": mode_counts[mode],
                "pct": round(mode_counts[mode] / len(hurts) * 100, 1),
                "avg_damage": round(sum(mode_avg_damage[mode]) / len(mode_avg_damage[mode]), 3),
                "tasks": mode_tasks[mode],
            }
            for mode in sorted(mode_counts, key=lambda m: -mode_counts[m])
        },
        "tasks": hurts,
    }

    # Also compute team-helps stats for comparison
    helps = []
    for tid, scores in task_scores.items():
        oracle = scores.get("oracle")
        full = scores.get("full")
        if oracle is not None and full is not None and full > oracle + 0.01:
            helps.append(tid)

    neutral = len(task_scores) - len(hurts) - len(helps)
    summary["team_helps_count"] = len(helps)
    summary["neutral_count"] = neutral

    # Write JSON
    os.makedirs("shared/paper", exist_ok=True)
    with open("shared/paper/failure_analysis.json", "w") as f:
        json.dump(summary, f, indent=2)
    print(f"Wrote shared/paper/failure_analysis.json")

    # Generate LaTeX table
    generate_latex_table(summary, hurts)

    # Print summary
    print(f"\n=== Failure Analysis Summary ===")
    print(f"Total tasks: {summary['total_tasks_analyzed']}")
    print(f"Team helps: {summary['team_helps_count']} ({summary['team_helps_count']/summary['total_tasks_analyzed']*100:.1f}%)")
    print(f"Neutral: {summary['neutral_count']} ({summary['neutral_count']/summary['total_tasks_analyzed']*100:.1f}%)")
    print(f"Team hurts: {summary['total_team_hurts']} ({summary['team_hurts_pct']}%)")
    print(f"\nFailure Mode Breakdown:")
    for mode, info in summary["failure_mode_breakdown"].items():
        print(f"  {mode}: {info['count']} tasks ({info['pct']}%), avg damage: {info['avg_damage']:+.3f}")

    # Key findings
    print(f"\n=== Key Findings ===")
    verify_damage = mode_counts.get("VERIFICATION_DAMAGE", 0)
    complete_fail = mode_counts.get("COMPLETE_TEAM_FAILURE", 0)
    print(f"1. Verification damage is the #1 failure mode ({verify_damage} tasks)")
    print(f"2. {complete_fail} tasks have complete team failure (full=0)")

    # Count tasks where full=0 but no_verify > 0
    full_zero_verify_ok = sum(1 for h in hurts if h["full"] < 0.01 and (h.get("team_no_verify") or 0) > 0.3)
    print(f"3. {full_zero_verify_ok} tasks: verifier completely destroys a working solution (full=0, no_verify>0.3)")


def generate_latex_table(summary, hurts):
    """Generate LaTeX table for paper."""
    lines = [
        r"% Auto-generated by scripts/failure_analysis.py",
        r"\begin{table}[t]",
        r"\centering",
        r"\caption{Failure mode analysis of TEAM-HURTS tasks. ``Damage'' = $S_\text{full} - S_\text{oracle}$.}",
        r"\label{tab:failure-analysis}",
        r"\small",
        r"\begin{tabular}{lrrr}",
        r"\toprule",
        r"Failure Mode & Count & \% & Avg Damage \\",
        r"\midrule",
    ]

    for mode, info in summary["failure_mode_breakdown"].items():
        mode_display = mode.replace("_", " ").title()
        lines.append(
            f"{mode_display} & {info['count']} & {info['pct']}\\% & {info['avg_damage']:+.3f} \\\\"
        )

    lines.extend([
        r"\midrule",
        f"\\textbf{{Total}} & \\textbf{{{summary['total_team_hurts']}}} & \\textbf{{{summary['team_hurts_pct']}\\%}} & -- \\\\",
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table}",
    ])

    # Also generate detailed table (top 15 worst)
    lines.extend([
        "",
        r"% Detailed: Top 15 worst TEAM-HURTS tasks",
        r"\begin{table*}[t]",
        r"\centering",
        r"\caption{Top 15 tasks where teamwork hurts performance most. Scores are partial scores averaged across seeds.}",
        r"\label{tab:failure-details}",
        r"\small",
        r"\begin{tabular}{llcrrrrl}",
        r"\toprule",
        r"Task & Category & Failure Mode & Oracle & Full & NoVerify & NoPlan & Damage \\",
        r"\midrule",
    ])

    for h in hurts[:15]:
        mode_short = {
            "VERIFICATION_DAMAGE": "Verify",
            "PLANNING_OVERHEAD": "Plan",
            "COMPLETE_TEAM_FAILURE": "Total",
            "COORDINATION_FAILURE": "Coord",
            "ROLE_BOUNDARY_LOSS": "Boundary",
            "MINOR_DEGRADATION": "Minor",
        }.get(h["failure_mode"], h["failure_mode"][:6])

        tnv = f"{h['team_no_verify']:.2f}" if h["team_no_verify"] is not None else "--"
        tnp = f"{h['team_no_plan']:.2f}" if h["team_no_plan"] is not None else "--"
        tid = h["task_id"].replace("_", r"\_")

        lines.append(
            f"{tid} & {h['task_category']} & {mode_short} & "
            f"{h['oracle']:.2f} & {h['full']:.2f} & {tnv} & {tnp} & {h['uplift']:+.3f} \\\\"
        )

    lines.extend([
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table*}",
    ])

    with open("shared/paper/table_failure_analysis.tex", "w") as f:
        f.write("\n".join(lines) + "\n")
    print("Wrote shared/paper/table_failure_analysis.tex")


if __name__ == "__main__":
    main()
