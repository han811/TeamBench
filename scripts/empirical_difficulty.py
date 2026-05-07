"""
Empirical difficulty recalibration using oracle scores across multiple models.

Loads all ablation results, computes per-task empirical difficulty as
1 - mean(oracle partial_scores), then compares against author-assigned labels.

Outputs:
  shared/paper/empirical_difficulty.json
  shared/paper/table_difficulty_calibration.tex
"""
from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Optional

import numpy as np
from scipy import stats


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
ABLATION_DIR = REPO_ROOT / "shared" / "ablation_results"
TASKS_DIR = REPO_ROOT / "tasks"
OUT_DIR = REPO_ROOT / "shared" / "paper"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Author difficulty → numeric
DIFFICULTY_MAP = {
    "easy": 0.25,
    "medium": 0.50,
    "hard": 0.75,
    "expert": 1.00,
}

# Empirical thresholds → recalibrated label
EMPIRICAL_THRESHOLDS = [
    (0.20, "easy"),
    (0.50, "medium"),
    (0.80, "hard"),
    (1.01, "expert"),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_runs(data: dict | list) -> list[dict]:
    """Return list of run dicts from a loaded JSON object, handling all formats."""
    if isinstance(data, list):
        return data
    # standard format: {"runs": [...]}
    for key in ("runs", "results", "data"):
        if key in data and isinstance(data[key], list):
            return data[key]
    return []


def _get_partial_score(run: dict) -> Optional[float]:
    """Extract partial_score from a run dict, handling both formats."""
    # Standard format
    if "partial_score" in run:
        v = run["partial_score"]
        if v is not None:
            return float(v)
    # Phase-3 format: {"secondary": {"partial_score": ...}}
    secondary = run.get("secondary")
    if isinstance(secondary, dict) and "partial_score" in secondary:
        v = secondary["partial_score"]
        if v is not None:
            return float(v)
    # Fall back to pass bool
    if "pass" in run:
        return 1.0 if run["pass"] else 0.0
    return None


def _is_oracle(run: dict) -> bool:
    return run.get("condition", "") == "oracle"


def load_all_runs(ablation_dir: Path) -> dict[str, list[float]]:
    """
    Returns: task_id -> list of oracle partial_scores (across all files/models).
    Skips non-ablation-format files (hetero, dynamic_deployment, ea_results, etc.).
    """
    oracle_scores: dict[str, list[float]] = defaultdict(list)
    skipped = []

    for fname in sorted(os.listdir(ablation_dir)):
        if not fname.endswith(".json"):
            continue
        # Skip files that don't contain standard ablation conditions
        skip_prefixes = (
            "hetero_", "dynamic_", "ea_results", "topology_",
            "scaling_", "strong_baseline",
        )
        if any(fname.startswith(p) for p in skip_prefixes):
            skipped.append(fname)
            continue

        fpath = ablation_dir / fname
        try:
            with open(fpath) as f:
                data = json.load(f)
        except Exception as e:
            print(f"  [WARN] Could not load {fname}: {e}", file=sys.stderr)
            continue

        runs = _extract_runs(data)
        if not runs:
            skipped.append(fname)
            continue

        file_oracle = 0
        for run in runs:
            if not _is_oracle(run):
                continue
            task_id = run.get("task_id", "")
            if not task_id:
                continue
            score = _get_partial_score(run)
            if score is None:
                continue
            oracle_scores[task_id].append(score)
            file_oracle += 1

        if file_oracle == 0:
            skipped.append(fname)

    if skipped:
        print(f"  [INFO] Skipped/no-oracle-runs in: {', '.join(skipped[:10])}"
              + (f" ... (+{len(skipped)-10} more)" if len(skipped) > 10 else ""),
              file=sys.stderr)
    return oracle_scores


def load_author_difficulties() -> dict[str, str]:
    """Parse difficulty from tasks/{task_id}/task.yaml."""
    difficulties: dict[str, str] = {}
    if not TASKS_DIR.exists():
        return difficulties
    for task_name in os.listdir(TASKS_DIR):
        yaml_path = TASKS_DIR / task_name / "task.yaml"
        if not yaml_path.exists():
            continue
        try:
            with open(yaml_path) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("difficulty:"):
                        val = line.split(":", 1)[1].strip().strip('"\'')
                        difficulties[task_name] = val
                        break
        except Exception:
            pass
    return difficulties


def recalibrate_label(empirical_diff: float) -> str:
    for threshold, label in EMPIRICAL_THRESHOLDS:
        if empirical_diff < threshold:
            return label
    return "expert"


# ---------------------------------------------------------------------------
# Equalizer Effect analysis
# ---------------------------------------------------------------------------

def equalizer_analysis(
    oracle_scores: dict[str, list[float]],
    all_runs: list[dict],
    n_quintiles: int = 5,
) -> dict:
    """
    Verify Equalizer Effect: does team uplift increase with task difficulty?

    Uses empirical difficulty (quintiles) and computes team_uplift per quintile.
    Also checks author-label quintiles for comparison.
    """
    # Compute per-task empirical difficulty
    emp_diff: dict[str, float] = {
        tid: 1.0 - float(np.mean(scores))
        for tid, scores in oracle_scores.items()
        if scores
    }

    # Collect full vs oracle scores per task
    task_full: dict[str, list[float]] = defaultdict(list)
    task_oracle: dict[str, list[float]] = defaultdict(list)
    for run in all_runs:
        cond = run.get("condition", "")
        tid = run.get("task_id", "")
        score = _get_partial_score(run)
        if not tid or score is None:
            continue
        if cond == "full":
            task_full[tid].append(score)
        elif cond == "oracle":
            task_oracle[tid].append(score)

    # Only tasks with both conditions and empirical difficulty
    tasks_with_data = [
        t for t in emp_diff
        if t in task_full and t in task_oracle
    ]

    if len(tasks_with_data) < n_quintiles:
        return {"error": f"Too few tasks with both conditions: {len(tasks_with_data)}"}

    difficulties = np.array([emp_diff[t] for t in tasks_with_data])
    uplifts = np.array([
        np.mean(task_full[t]) - np.mean(task_oracle[t])
        for t in tasks_with_data
    ])

    # Quintile boundaries
    quintile_edges = np.percentile(difficulties, np.linspace(0, 100, n_quintiles + 1))
    quintile_data = []
    for i in range(n_quintiles):
        lo, hi = quintile_edges[i], quintile_edges[i + 1]
        mask = (difficulties >= lo) & (difficulties <= hi)
        if mask.sum() == 0:
            continue
        q_uplifts = uplifts[mask]
        q_diffs = difficulties[mask]
        quintile_data.append({
            "quintile": i + 1,
            "diff_range": [float(lo), float(hi)],
            "n_tasks": int(mask.sum()),
            "mean_empirical_difficulty": float(np.mean(q_diffs)),
            "mean_team_uplift": float(np.mean(q_uplifts)),
            "std_team_uplift": float(np.std(q_uplifts)),
        })

    # Spearman between difficulty and uplift
    rho, pval = stats.spearmanr(difficulties, uplifts)

    return {
        "quintiles": quintile_data,
        "spearman_rho": float(rho),
        "spearman_pval": float(pval),
        "n_tasks": len(tasks_with_data),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("Loading oracle scores from all ablation files...")
    oracle_scores = load_all_runs(ABLATION_DIR)
    print(f"  Found oracle runs for {len(oracle_scores)} unique tasks.")

    print("Loading author difficulties from task.yaml files...")
    author_difficulties = load_author_difficulties()
    print(f"  Found difficulty labels for {len(author_difficulties)} tasks.")

    # Compute per-task empirical difficulty
    task_analysis: list[dict] = []
    for task_id, scores in sorted(oracle_scores.items()):
        emp_diff = 1.0 - float(np.mean(scores))
        emp_label = recalibrate_label(emp_diff)
        author_label = author_difficulties.get(task_id, "unknown")
        author_numeric = DIFFICULTY_MAP.get(author_label, None)
        task_analysis.append({
            "task_id": task_id,
            "n_oracle_runs": len(scores),
            "mean_oracle_score": float(np.mean(scores)),
            "std_oracle_score": float(np.std(scores)) if len(scores) > 1 else 0.0,
            "empirical_difficulty": emp_diff,
            "empirical_label": emp_label,
            "author_label": author_label,
            "author_numeric": author_numeric,
        })

    # Filter to tasks with known author labels for correlation
    corr_tasks = [t for t in task_analysis if t["author_numeric"] is not None]
    print(f"\n  {len(corr_tasks)} tasks have both empirical difficulty and author labels.")

    spearman_rho, spearman_pval = None, None
    if len(corr_tasks) >= 5:
        author_vals = np.array([t["author_numeric"] for t in corr_tasks])
        emp_vals = np.array([t["empirical_difficulty"] for t in corr_tasks])
        spearman_rho, spearman_pval = stats.spearmanr(author_vals, emp_vals)
        print(f"  Spearman correlation (author vs empirical): rho={spearman_rho:.3f}, p={spearman_pval:.4f}")

    # Recalibration agreement
    agreement = sum(1 for t in corr_tasks if t["empirical_label"] == t["author_label"])
    print(f"  Label agreement (author == recalibrated): {agreement}/{len(corr_tasks)} ({100*agreement/max(1,len(corr_tasks)):.1f}%)")

    # Cross-tabulation
    label_order = ["easy", "medium", "hard", "expert"]
    crosstab: dict[str, dict[str, int]] = {a: {e: 0 for e in label_order} for a in label_order}
    for t in corr_tasks:
        al = t["author_label"]
        el = t["empirical_label"]
        if al in crosstab and el in label_order:
            crosstab[al][el] += 1

    # Equalizer Effect with empirical difficulty
    print("\nAnalyzing Equalizer Effect with empirical difficulty quintiles...")
    # Load all runs once for uplift computation
    all_runs: list[dict] = []
    for fname in sorted(os.listdir(ABLATION_DIR)):
        if not fname.endswith(".json"):
            continue
        skip_prefixes = ("hetero_", "dynamic_", "ea_results", "topology_", "scaling_", "strong_baseline")
        if any(fname.startswith(p) for p in skip_prefixes):
            continue
        try:
            with open(ABLATION_DIR / fname) as f:
                data = json.load(f)
            all_runs.extend(_extract_runs(data))
        except Exception:
            pass

    equalizer = equalizer_analysis(oracle_scores, all_runs)
    if "error" not in equalizer:
        rho = equalizer["spearman_rho"]
        pval = equalizer["spearman_pval"]
        print(f"  Spearman(empirical_difficulty, team_uplift): rho={rho:.3f}, p={pval:.4f}")
        for q in equalizer["quintiles"]:
            print(f"  Q{q['quintile']} (diff={q['mean_empirical_difficulty']:.2f}): "
                  f"uplift={q['mean_team_uplift']:+.3f} (n={q['n_tasks']})")
        if spearman_pval is not None:
            stronger = "STRONGER" if abs(rho) > abs(spearman_rho) else "WEAKER"
            print(f"\n  Equalizer Effect correlation with empirical difficulty is {stronger} "
                  f"than with author labels (|rho|={abs(rho):.3f} vs {abs(spearman_rho):.3f})")
    else:
        print(f"  [WARN] Equalizer analysis: {equalizer['error']}")

    # Scatter plot data (author numeric vs empirical)
    scatter_data = [
        {"x": t["author_numeric"], "y": t["empirical_difficulty"], "task_id": t["task_id"]}
        for t in corr_tasks
    ]

    # Build output JSON
    output = {
        "summary": {
            "n_tasks_with_oracle_runs": len(oracle_scores),
            "n_tasks_with_author_labels": len(corr_tasks),
            "spearman_rho_author_vs_empirical": float(spearman_rho) if spearman_rho is not None else None,
            "spearman_pval_author_vs_empirical": float(spearman_pval) if spearman_pval is not None else None,
            "label_agreement_pct": float(100 * agreement / max(1, len(corr_tasks))),
        },
        "per_task": task_analysis,
        "scatter_data": scatter_data,
        "cross_tabulation": {
            "rows_author_label": label_order,
            "cols_empirical_label": label_order,
            "matrix": [[crosstab[a][e] for e in label_order] for a in label_order],
        },
        "equalizer_effect": equalizer,
    }

    out_json = OUT_DIR / "empirical_difficulty.json"
    with open(out_json, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nWrote {out_json}")

    # ---------------------------------------------------------------------------
    # LaTeX table
    # ---------------------------------------------------------------------------
    lines: list[str] = []
    lines.append(r"\begin{table}[htbp]")
    lines.append(r"\centering")
    lines.append(r"\caption{Author vs.\ Empirical Difficulty Calibration. "
                 r"Empirical difficulty $= 1 - \bar{s}_{\text{oracle}}$ "
                 r"averaged across all models and seeds. "
                 r"Recalibrated labels use thresholds: "
                 r"easy $<$ 0.20, medium 0.20--0.50, hard 0.50--0.80, expert $>$ 0.80.}")
    lines.append(r"\label{tab:difficulty_calibration}")
    lines.append(r"\small")
    lines.append(r"\begin{tabular}{lcccc}")
    lines.append(r"\toprule")
    lines.append(r"Author Label & \multicolumn{4}{c}{Recalibrated (Empirical) Label} \\")
    lines.append(r"\cmidrule(lr){2-5}")
    lines.append(r" & Easy & Medium & Hard & Expert \\")
    lines.append(r"\midrule")
    for al in label_order:
        row_counts = [crosstab[al][el] for el in label_order]
        total = sum(row_counts)
        if total == 0:
            continue
        cells = " & ".join(
            r"\textbf{" + str(c) + r"}" if al == el else str(c)
            for el, c in zip(label_order, row_counts)
        )
        lines.append(rf"{al.capitalize()} & {cells} \\")
    lines.append(r"\midrule")
    # Totals row
    totals = [sum(crosstab[al][el] for al in label_order) for el in label_order]
    lines.append(r"Total & " + " & ".join(str(t) for t in totals) + r" \\")
    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}")

    # Stats note
    if spearman_rho is not None:
        sig = "***" if spearman_pval < 0.001 else ("**" if spearman_pval < 0.01 else ("*" if spearman_pval < 0.05 else "n.s."))
        lines.append(r"\begin{tablenotes}\small")
        lines.append(rf"\item Spearman $\rho = {spearman_rho:.3f}$ ({sig}, $p = {spearman_pval:.4f}$, "
                     rf"$n = {len(corr_tasks)}$ tasks). "
                     rf"Diagonal cells (bold) indicate agreement between author and recalibrated labels "
                     rf"({agreement}/{len(corr_tasks)}, {100*agreement//max(1,len(corr_tasks))}\%).")
        lines.append(r"\end{tablenotes}")
    lines.append(r"\end{table}")

    out_tex = OUT_DIR / "table_difficulty_calibration.tex"
    with open(out_tex, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"Wrote {out_tex}")

    # Print summary table to stdout
    print("\n--- Difficulty Cross-Tabulation (rows=author, cols=recalibrated) ---")
    header = f"{'Author':<10}" + "".join(f"{l.capitalize():>10}" for l in label_order) + f"{'Total':>10}"
    print(header)
    print("-" * len(header))
    for al in label_order:
        row_counts = [crosstab[al][el] for el in label_order]
        total = sum(row_counts)
        if total == 0:
            continue
        row = f"{al.capitalize():<10}" + "".join(f"{c:>10}" for c in row_counts) + f"{total:>10}"
        print(row)

    print("\n--- Top-10 Most Miscalibrated Tasks (|author_numeric - empirical|) ---")
    miscal = sorted(
        [t for t in corr_tasks if t["author_numeric"] is not None],
        key=lambda t: abs(t["author_numeric"] - t["empirical_difficulty"]),
        reverse=True,
    )
    print(f"{'Task':<35} {'Author':>8} {'Empirical':>10} {'Delta':>8}")
    for t in miscal[:10]:
        delta = t["author_numeric"] - t["empirical_difficulty"]
        print(f"{t['task_id']:<35} {t['author_label']:>8} {t['empirical_difficulty']:>10.3f} {delta:>+8.3f}")


if __name__ == "__main__":
    main()
