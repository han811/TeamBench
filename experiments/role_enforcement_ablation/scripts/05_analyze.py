"""05_analyze.py.

Consolidate role-enforcement ablation runs, run pre-registered tests, and emit
paper assets.

Pre-registered tests (HYPOTHESIS.md):
    T1  prompt_only vs enforced on role-violation rate (McNemar)
    T2  prompt_only vs enforced on task-success rate  (McNemar)
    T3  enforced_shared_history vs enforced on task-success rate (McNemar)

Holm-Bonferroni over {T1, T2, T3}.

Inputs:
    runs/<model>/results_<condition>.json      (from 03_run_all.sh)
    analysis/role_compliance.jsonl             (from 04_score_compliance.py)
    config/task_selection.json

Outputs:
    analysis/consolidated.json
    analysis/statistics.json
    analysis/tables/table_main_effect.tex
    analysis/tables/table_compliance.tex
    analysis/figures/fig_compliance_by_condition.pdf
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))
from harness.statistics import bootstrap_ci, bootstrap_ci_difference, mcnemar_test  # noqa: E402

EXP_DIR = Path(__file__).resolve().parent.parent
CONDITIONS = ("prompt_only", "enforced", "enforced_shared_history")


def load_results(runs_dir: Path) -> list[dict]:
    """Merge per-model results_<condition>.json into a flat per-run list.
    Per the pre-registered exclusion criterion (HYPOTHESIS.md), runs with
    non-retryable API errors after retries are excluded from primary analysis.
    """
    out: list[dict] = []
    n_excluded = 0
    for model_dir in sorted(runs_dir.iterdir()):
        if not model_dir.is_dir() or model_dir.name == "smoke_test":
            continue
        for f in sorted(model_dir.glob("results_*.json")):
            try:
                d = json.loads(f.read_text())
            except Exception:
                continue
            for run in d.get("runs") or []:
                err = run.get("error")
                if err:
                    n_excluded += 1
                    continue
                secondary = run.get("secondary") or {}
                out.append({
                    "model": model_dir.name,
                    "condition": run.get("condition"),
                    "task_id": run.get("task_id"),
                    "seed": run.get("seed"),
                    "run_id": run.get("run_id"),
                    "pass": bool(run.get("pass", False)),
                    "partial_score": float(
                        secondary.get("partial_score", run.get("partial_score", 0.0))
                    ),
                })
    if n_excluded:
        print(f"  load_results: excluded {n_excluded} errored runs", file=sys.stderr)
    return out


def load_compliance(path: Path) -> dict:
    """Return (model, condition, task_id, seed, run_id) -> violation_rate."""
    per_run_total: dict[tuple, int] = defaultdict(int)
    per_run_viol: dict[tuple, int] = defaultdict(int)
    if not path.exists():
        return {}
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        try:
            r = json.loads(line)
        except Exception:
            continue
        key = (r["model"], r["condition"], r["task_id"], int(r["seed"]), r["run_id"])
        per_run_total[key] += 1
        if r.get("violation"):
            per_run_viol[key] += 1
    return {
        k: per_run_viol[k] / per_run_total[k]
        for k in per_run_total
        if per_run_total[k] > 0
    }


def align_paired(runs: list[dict], cond_a: str, cond_b: str, metric: str) -> tuple[list, list]:
    """Pair runs on (model, task_id, seed). metric = 'pass' or 'violation_rate'."""
    index = {}
    for r in runs:
        key = (r["model"], r["task_id"], r["seed"])
        index.setdefault(key, {})[r["condition"]] = r
    a_vals, b_vals = [], []
    for key, by_cond in index.items():
        if cond_a in by_cond and cond_b in by_cond:
            va = by_cond[cond_a].get(metric)
            vb = by_cond[cond_b].get(metric)
            if va is None or vb is None:
                continue
            a_vals.append(bool(va) if metric == "pass" else float(va))
            b_vals.append(bool(vb) if metric == "pass" else float(vb))
    return a_vals, b_vals


def holm_bonferroni(pvals: list[float]) -> list[float]:
    n = len(pvals)
    ordered = sorted(enumerate(pvals), key=lambda x: x[1])
    adjusted = [0.0] * n
    running_max = 0.0
    for rank, (orig_ix, p) in enumerate(ordered):
        p_adj = min(1.0, (n - rank) * p)
        running_max = max(running_max, p_adj)
        adjusted[orig_ix] = running_max
    return adjusted


def attach_compliance(runs: list[dict], compliance: dict) -> None:
    for r in runs:
        key = (r["model"], r["condition"], r["task_id"], r["seed"], r["run_id"])
        r["violation_rate"] = compliance.get(key, None)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs-dir", default=str(EXP_DIR / "runs"))
    ap.add_argument("--compliance", default=str(EXP_DIR / "analysis" / "role_compliance.jsonl"))
    ap.add_argument("--out-dir", default=str(EXP_DIR / "analysis"))
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    runs = load_results(Path(args.runs_dir))
    compliance = load_compliance(Path(args.compliance))
    attach_compliance(runs, compliance)

    (out_dir / "consolidated.json").write_text(json.dumps(runs, indent=2) + "\n")

    if not runs:
        print("No runs yet. Launch 03_run_all.sh first.", file=sys.stderr)
        return 0

    # T1 — compliance, prompt_only vs enforced
    a1, b1 = align_paired(runs, "prompt_only", "enforced", "violation_rate")
    a1_bin = [x is not None and x > 0 for x in a1]
    b1_bin = [x is not None and x > 0 for x in b1]
    t1_stat, t1_p = mcnemar_test(a1_bin, b1_bin) if a1_bin else (0.0, 1.0)

    # T2 — outcome, prompt_only vs enforced
    a2, b2 = align_paired(runs, "prompt_only", "enforced", "pass")
    t2_stat, t2_p = mcnemar_test(a2, b2) if a2 else (0.0, 1.0)

    # T3 — outcome, enforced_shared_history vs enforced
    a3, b3 = align_paired(runs, "enforced_shared_history", "enforced", "pass")
    t3_stat, t3_p = mcnemar_test(a3, b3) if a3 else (0.0, 1.0)

    pvals = [t1_p, t2_p, t3_p]
    adj = holm_bonferroni(pvals)

    # Per-condition headline rates
    by_cond = defaultdict(list)
    comp_by_cond = defaultdict(list)
    for r in runs:
        by_cond[r["condition"]].append(bool(r["pass"]))
        if r.get("violation_rate") is not None:
            comp_by_cond[r["condition"]].append(float(r["violation_rate"]))

    def _summ(vs: list[float]) -> dict:
        if not vs:
            return {"n": 0, "mean": None, "ci_low": None, "ci_high": None}
        mean, lo, hi = bootstrap_ci(list(map(float, vs)), n_bootstrap=2000, alpha=0.05)
        return {"n": len(vs), "mean": mean, "ci_low": lo, "ci_high": hi}

    stats = {
        "n_runs_total": len(runs),
        "per_condition_pass_rate": {c: _summ(by_cond[c]) for c in CONDITIONS},
        "per_condition_violation_rate": {c: _summ(comp_by_cond[c]) for c in CONDITIONS},
        "tests": {
            "T1_compliance_prompt_vs_enforced": {
                "n_pairs": len(a1_bin),
                "stat": t1_stat,
                "p_raw": t1_p,
                "p_holm": adj[0],
            },
            "T2_outcome_prompt_vs_enforced": {
                "n_pairs": len(a2),
                "stat": t2_stat,
                "p_raw": t2_p,
                "p_holm": adj[1],
            },
            "T3_outcome_sharedhist_vs_enforced": {
                "n_pairs": len(a3),
                "stat": t3_stat,
                "p_raw": t3_p,
                "p_holm": adj[2],
            },
        },
    }
    (out_dir / "statistics.json").write_text(json.dumps(stats, indent=2) + "\n")

    # Minimal LaTeX table
    tbl_dir = out_dir / "tables"
    tbl_dir.mkdir(exist_ok=True)
    lines = [
        "\\begin{tabular}{lccc}",
        "\\toprule",
        "Metric & prompt\\_only & enforced & enf\\_shared\\_history \\\\",
        "\\midrule",
    ]
    pr = stats["per_condition_pass_rate"]
    vr = stats["per_condition_violation_rate"]

    def _cell(s: dict) -> str:
        if s.get("mean") is None:
            return "--"
        return f"{s['mean']*100:.1f}\\% [{s['ci_low']*100:.1f},{s['ci_high']*100:.1f}] (n={s['n']})"

    lines.append(
        "Pass rate & "
        + " & ".join(_cell(pr[c]) for c in CONDITIONS) + " \\\\"
    )
    lines.append(
        "Violation rate & "
        + " & ".join(_cell(vr[c]) for c in CONDITIONS) + " \\\\"
    )
    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    (tbl_dir / "table_main_effect.tex").write_text("\n".join(lines) + "\n")

    print("Wrote", out_dir / "statistics.json")
    print("Wrote", tbl_dir / "table_main_effect.tex")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
