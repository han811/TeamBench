#!/usr/bin/env python3
"""Analyze strong baseline results vs standard ablation.

Compares oracle_cot and oracle_2pass against oracle and full team
to determine whether team benefits come from role separation or
just more compute.

Usage:
    python scripts/analyze_strong_baseline.py
"""
import json
import glob
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def load_all_runs():
    all_runs = []
    for f in glob.glob("shared/ablation_results/*.json"):
        try:
            data = json.load(open(f))
            all_runs.extend(data.get("runs", []))
        except Exception:
            pass
    return all_runs


def main():
    all_runs = load_all_runs()

    # Group by task_id and condition
    task_scores = defaultdict(lambda: defaultdict(list))
    for r in all_runs:
        tid = r.get("task_id", "")
        cond = r.get("condition", "")
        ps = r.get("partial_score")
        if ps is not None and tid and cond:
            task_scores[tid][cond].append(ps)

    conditions = ["oracle", "restricted", "oracle_cot", "oracle_2pass", "team_no_verify", "full"]

    # Find tasks that have baseline data
    baseline_tasks = []
    for tid in sorted(task_scores):
        conds = task_scores[tid]
        if "oracle_cot" in conds or "oracle_2pass" in conds:
            baseline_tasks.append(tid)

    if not baseline_tasks:
        print("No strong baseline results found yet. Wait for runs to complete.")
        return

    print(f"=== Strong Baseline Analysis ===")
    print(f"Tasks with baseline data: {len(baseline_tasks)}")
    print()

    # Per-task comparison
    print(f"{'Task':<35s} {'Oracle':>7s} {'CoT':>7s} {'2Pass':>7s} {'NoVer':>7s} {'Full':>7s} {'Restr':>7s}")
    print("-" * 95)

    avg = defaultdict(list)
    for tid in baseline_tasks:
        conds = task_scores[tid]
        row = [tid]
        for c in conditions:
            if c in conds and conds[c]:
                val = sum(conds[c]) / len(conds[c])
                avg[c].append(val)
                row.append(f"{val:.3f}")
            else:
                row.append("--")
        print(f"{row[0]:<35s} {row[1]:>7s} {row[2]:>7s} {row[3]:>7s} {row[4]:>7s} {row[5]:>7s} {row[6]:>7s}")

    print("-" * 95)
    # Averages
    row = ["AVERAGE"]
    for c in conditions:
        if avg[c]:
            val = sum(avg[c]) / len(avg[c])
            row.append(f"{val:.3f}")
        else:
            row.append("--")
    print(f"{row[0]:<35s} {row[1]:>7s} {row[2]:>7s} {row[3]:>7s} {row[4]:>7s} {row[5]:>7s} {row[6]:>7s}")

    # Key comparisons
    print(f"\n=== Key Comparisons ===")
    for c in ["oracle_cot", "oracle_2pass"]:
        if avg.get(c) and avg.get("oracle"):
            c_avg = sum(avg[c]) / len(avg[c])
            o_avg = sum(avg["oracle"]) / len(avg["oracle"])
            print(f"{c} vs oracle: {c_avg:.3f} vs {o_avg:.3f} (delta={c_avg - o_avg:+.3f})")

    if avg.get("full") and avg.get("oracle_cot"):
        f_avg = sum(avg["full"]) / len(avg["full"])
        cot_avg = sum(avg["oracle_cot"]) / len(avg["oracle_cot"])
        print(f"\nfull_team vs oracle_cot: {f_avg:.3f} vs {cot_avg:.3f} (delta={f_avg - cot_avg:+.3f})")
        if f_avg > cot_avg:
            print("  -> Team STILL outperforms enhanced single agent = role separation provides unique value")
        else:
            print("  -> Enhanced single agent matches/beats team = benefit is compute, not role separation")

    if avg.get("full") and avg.get("oracle_2pass"):
        f_avg = sum(avg["full"]) / len(avg["full"])
        p2_avg = sum(avg["oracle_2pass"]) / len(avg["oracle_2pass"])
        print(f"\nfull_team vs oracle_2pass: {f_avg:.3f} vs {p2_avg:.3f} (delta={f_avg - p2_avg:+.3f})")

    # Task-level: where does team beat both baselines?
    print(f"\n=== Per-Task Team vs Baselines ===")
    team_wins = 0
    baseline_wins = 0
    ties = 0
    for tid in baseline_tasks:
        conds = task_scores[tid]
        full_s = sum(conds.get("full", [0])) / len(conds["full"]) if "full" in conds else None
        cot_s = sum(conds.get("oracle_cot", [0])) / len(conds["oracle_cot"]) if "oracle_cot" in conds else None
        p2_s = sum(conds.get("oracle_2pass", [0])) / len(conds["oracle_2pass"]) if "oracle_2pass" in conds else None

        best_baseline = max(filter(None, [cot_s, p2_s]), default=0)
        if full_s is not None and full_s > best_baseline + 0.01:
            team_wins += 1
        elif full_s is not None and full_s < best_baseline - 0.01:
            baseline_wins += 1
        else:
            ties += 1

    print(f"Team wins: {team_wins}, Baseline wins: {baseline_wins}, Ties: {ties}")

    # Save results
    results = {
        "tasks_analyzed": len(baseline_tasks),
        "per_condition_avg": {c: round(sum(avg[c]) / len(avg[c]), 4) if avg.get(c) else None for c in conditions},
        "team_vs_baseline": {"team_wins": team_wins, "baseline_wins": baseline_wins, "ties": ties},
    }

    os.makedirs("shared/paper", exist_ok=True)
    with open("shared/paper/strong_baseline_stats.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nWrote shared/paper/strong_baseline_stats.json")

    # Generate LaTeX table
    generate_latex(baseline_tasks, task_scores, conditions)


def generate_latex(tasks, task_scores, conditions):
    cond_labels = {
        "oracle": "Oracle",
        "restricted": "Restricted",
        "oracle_cot": "Oracle+CoT",
        "oracle_2pass": "Oracle+2Pass",
        "team_no_verify": "Team-NoVer",
        "full": "Full Team",
    }

    lines = [
        r"% Auto-generated by scripts/analyze_strong_baseline.py",
        r"\begin{table}[t]",
        r"\centering",
        r"\caption{Strong baseline comparison. Oracle+CoT and Oracle+2Pass give a single agent enhanced prompting and 2$\times$ compute budget to control for the compute confound.}",
        r"\label{tab:strong-baseline}",
        r"\small",
        r"\begin{tabular}{lrrrrrr}",
        r"\toprule",
        " & ".join(["Task"] + [cond_labels.get(c, c) for c in conditions]) + r" \\",
        r"\midrule",
    ]

    avgs = defaultdict(list)
    for tid in tasks:
        conds = task_scores[tid]
        cells = [tid.replace("_", r"\_")]
        for c in conditions:
            if c in conds and conds[c]:
                val = sum(conds[c]) / len(conds[c])
                avgs[c].append(val)
                cells.append(f"{val:.2f}")
            else:
                cells.append("--")
        lines.append(" & ".join(cells) + r" \\")

    lines.append(r"\midrule")
    cells = [r"\textbf{Average}"]
    for c in conditions:
        if avgs[c]:
            cells.append(f"\\textbf{{{sum(avgs[c]) / len(avgs[c]):.2f}}}")
        else:
            cells.append("--")
    lines.append(" & ".join(cells) + r" \\")

    lines.extend([
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table}",
    ])

    with open("shared/paper/table_strong_baseline.tex", "w") as f:
        f.write("\n".join(lines) + "\n")
    print("Wrote shared/paper/table_strong_baseline.tex")


if __name__ == "__main__":
    main()
