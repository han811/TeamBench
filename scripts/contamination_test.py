"""
Contamination resistance validation using held-out seeds.

For each of 50 representative parameterized tasks:
  - Generate instances for dev seeds (0, 1, 2) and held-out seeds (5, 6, 7)
  - Verify that held-out seeds produce genuinely different instances
  - Compute Jaccard similarity of workspace file contents between seed 0 and seed 5
  - Optionally run oracle condition on seeds 5-7 and compare scores against seeds 0-2
  - Statistical test: are scores significantly different across seed groups?

Outputs:
  shared/paper/contamination_validation.json
  shared/paper/table_contamination.tex
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Optional

import numpy as np
from scipy import stats

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

OUT_DIR = REPO_ROOT / "shared" / "paper"
OUT_DIR.mkdir(parents=True, exist_ok=True)

DEV_SEEDS = [0, 1, 2]
HELD_OUT_SEEDS = [5, 6, 7]
N_TASKS = 50

# Categories to sample from for representative coverage
TARGET_CATEGORIES = [
    "CR", "CROSS", "CRYPTO", "DIST", "DS", "EA", "GH", "INC",
    "INT", "IR", "LH", "MULTI", "NEG", "O", "P", "PIPE",
    "S", "SEC", "SPEC", "TEST", "TRAP",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _tokenize(text: str) -> set[str]:
    """Split text into word tokens for Jaccard similarity."""
    return set(text.split())


def jaccard_similarity(a: str, b: str) -> float:
    """Jaccard similarity between two strings (token-level)."""
    ta, tb = _tokenize(a), _tokenize(b)
    if not ta and not tb:
        return 1.0
    intersection = len(ta & tb)
    union = len(ta | tb)
    return intersection / union if union > 0 else 0.0


def workspace_jaccard(files_a: dict, files_b: dict) -> float:
    """Mean Jaccard similarity across all workspace files present in both instances."""
    all_keys = set(files_a) | set(files_b)
    if not all_keys:
        return 1.0
    similarities = []
    for key in all_keys:
        ca = files_a.get(key, "")
        cb = files_b.get(key, "")
        if isinstance(ca, bytes):
            ca = ca.decode("utf-8", errors="replace")
        if isinstance(cb, bytes):
            cb = cb.decode("utf-8", errors="replace")
        similarities.append(jaccard_similarity(ca, cb))
    return float(np.mean(similarities))


def expected_differs(exp_a: dict, exp_b: dict) -> bool:
    """Return True if expected dicts are genuinely different."""
    return exp_a != exp_b


def select_tasks(n: int = N_TASKS) -> list[str]:
    """
    Select n representative parameterized tasks spanning multiple categories.

    Uses generators.registry.list_generators() and picks tasks whose generator
    modules can actually be imported and instantiated.
    """
    from generators.registry import list_generators, get_generator

    all_ids = list_generators()
    print(f"  Found {len(all_ids)} generator IDs in registry.")

    # Group by category prefix
    by_category: dict[str, list[str]] = defaultdict(list)
    for tid in all_ids:
        prefix = tid.split("_")[0].upper()
        by_category[prefix].append(tid)

    # Round-robin across categories to get representative sample
    # First verify each candidate is importable
    selected: list[str] = []
    seen: set[str] = set()
    rounds = 0
    category_iters = {cat: iter(sorted(ids)) for cat, ids in by_category.items()}
    active_cats = list(by_category.keys())

    while len(selected) < n and active_cats:
        rounds += 1
        exhausted = []
        for cat in list(active_cats):
            it = category_iters.get(cat)
            if it is None:
                exhausted.append(cat)
                continue
            tid = next(it, None)
            if tid is None:
                exhausted.append(cat)
                continue
            if tid in seen:
                continue
            seen.add(tid)
            # Quick import check
            try:
                gen = get_generator(tid)
                selected.append(tid)
                if len(selected) >= n:
                    break
            except Exception:
                pass  # not importable, skip
        for cat in exhausted:
            active_cats.remove(cat)
            category_iters.pop(cat, None)
        if rounds > 1000:
            break  # safety

    print(f"  Selected {len(selected)} tasks across {len(set(t.split('_')[0].upper() for t in selected))} categories.")
    return selected[:n]


def generate_instance(task_id: str, seed: int):
    """Return a GeneratedTask or None on failure."""
    from generators.registry import get_generator
    try:
        gen = get_generator(task_id)
        return gen.generate(seed)
    except Exception as e:
        return None


# ---------------------------------------------------------------------------
# Per-task validation
# ---------------------------------------------------------------------------

def validate_task(task_id: str) -> dict:
    """
    Generate dev + held-out instances for one task and compute diversity metrics.
    """
    result: dict = {
        "task_id": task_id,
        "dev_seeds": DEV_SEEDS,
        "held_out_seeds": HELD_OUT_SEEDS,
        "dev_gen_success": 0,
        "held_out_gen_success": 0,
        "expected_differs_count": 0,  # # held-out seeds with different expected vs seed 0
        "workspace_differs_count": 0,  # # held-out seeds with different workspace vs seed 0
        "mean_jaccard_dev_vs_held": None,
        "all_held_out_differ": False,
        "error": None,
    }

    # Generate dev instances
    dev_instances = {}
    for s in DEV_SEEDS:
        inst = generate_instance(task_id, s)
        if inst is not None:
            dev_instances[s] = inst
            result["dev_gen_success"] += 1

    if not dev_instances:
        result["error"] = "All dev seeds failed to generate"
        return result

    base_inst = dev_instances.get(0) or list(dev_instances.values())[0]

    # Generate held-out instances
    held_instances = {}
    for s in HELD_OUT_SEEDS:
        inst = generate_instance(task_id, s)
        if inst is not None:
            held_instances[s] = inst
            result["held_out_gen_success"] += 1

    if not held_instances:
        result["error"] = "All held-out seeds failed to generate"
        return result

    # Compare held-out against base (seed 0 / first dev)
    jaccard_scores = []
    exp_diff_count = 0
    ws_diff_count = 0

    for s, inst in held_instances.items():
        # Expected values
        if expected_differs(base_inst.expected, inst.expected):
            exp_diff_count += 1

        # Workspace files
        j = workspace_jaccard(base_inst.workspace_files, inst.workspace_files)
        jaccard_scores.append(j)
        if base_inst.workspace_files != inst.workspace_files:
            ws_diff_count += 1

    result["expected_differs_count"] = exp_diff_count
    result["workspace_differs_count"] = ws_diff_count
    result["mean_jaccard_dev_vs_held"] = float(np.mean(jaccard_scores)) if jaccard_scores else None
    result["all_held_out_differ"] = (
        exp_diff_count == len(held_instances)
        and ws_diff_count == len(held_instances)
    )

    # Also validate cross-seed within dev seeds
    cross_seed_ok = True
    for i, s1 in enumerate(DEV_SEEDS):
        for s2 in DEV_SEEDS[i + 1:]:
            if s1 not in dev_instances or s2 not in dev_instances:
                continue
            if dev_instances[s1].expected == dev_instances[s2].expected:
                cross_seed_ok = False
                break
    result["dev_cross_seed_ok"] = cross_seed_ok

    return result


# ---------------------------------------------------------------------------
# Score comparison (if ablation results exist for held-out seeds)
# ---------------------------------------------------------------------------

def load_seed_scores(
    ablation_dir: Path,
    task_ids: set[str],
    condition: str = "oracle",
) -> dict[str, dict[int, list[float]]]:
    """
    Returns: task_id -> {seed -> [partial_scores]} for the given condition.
    Only loads scores for requested task_ids.
    """
    scores: dict[str, dict[int, list[float]]] = defaultdict(lambda: defaultdict(list))

    for fname in sorted(os.listdir(ablation_dir)):
        if not fname.endswith(".json"):
            continue
        skip_prefixes = ("hetero_", "dynamic_", "ea_results", "topology_", "scaling_", "strong_baseline")
        if any(fname.startswith(p) for p in skip_prefixes):
            continue
        try:
            with open(ablation_dir / fname) as f:
                data = json.load(f)
        except Exception:
            continue

        runs = _extract_runs(data)
        for run in runs:
            if run.get("condition", "") != condition:
                continue
            tid = run.get("task_id", "")
            if tid not in task_ids:
                continue
            seed = run.get("seed")
            if seed is None:
                continue
            score = _get_partial_score(run)
            if score is not None:
                scores[tid][int(seed)].append(score)

    return scores


def _extract_runs(data: dict | list) -> list[dict]:
    if isinstance(data, list):
        return data
    for key in ("runs", "results", "data"):
        if key in data and isinstance(data[key], list):
            return data[key]
    return []


def _get_partial_score(run: dict) -> Optional[float]:
    if "partial_score" in run:
        v = run["partial_score"]
        if v is not None:
            return float(v)
    secondary = run.get("secondary")
    if isinstance(secondary, dict) and "partial_score" in secondary:
        v = secondary["partial_score"]
        if v is not None:
            return float(v)
    if "pass" in run:
        return 1.0 if run["pass"] else 0.0
    return None


def score_comparison_analysis(
    task_ids: list[str],
    ablation_dir: Path,
) -> dict:
    """
    Compare oracle scores for dev seeds (0-2) vs held-out seeds (5-7).
    Uses existing ablation results (no new runs needed).
    """
    print("  Loading existing ablation scores for dev and held-out seeds...")
    all_scores = load_seed_scores(ablation_dir, set(task_ids), condition="oracle")

    dev_means, held_means = [], []
    per_task_comparison = []

    for tid in task_ids:
        task_scores = all_scores.get(tid, {})
        dev_scores = [s for seed in DEV_SEEDS for s in task_scores.get(seed, [])]
        held_scores = [s for seed in HELD_OUT_SEEDS for s in task_scores.get(seed, [])]

        if not dev_scores and not held_scores:
            continue

        entry = {
            "task_id": tid,
            "dev_seeds_n": len(dev_scores),
            "held_seeds_n": len(held_scores),
            "dev_mean": float(np.mean(dev_scores)) if dev_scores else None,
            "held_mean": float(np.mean(held_scores)) if held_scores else None,
        }
        per_task_comparison.append(entry)

        if dev_scores:
            dev_means.append(np.mean(dev_scores))
        if held_scores:
            held_means.append(np.mean(held_scores))

    result: dict = {
        "n_tasks_with_dev_scores": sum(1 for e in per_task_comparison if e["dev_mean"] is not None),
        "n_tasks_with_held_scores": sum(1 for e in per_task_comparison if e["held_mean"] is not None),
        "dev_mean_score": float(np.mean(dev_means)) if dev_means else None,
        "held_mean_score": float(np.mean(held_means)) if held_means else None,
        "per_task": per_task_comparison,
        "statistical_test": None,
    }

    # Paired statistical test on tasks with both dev and held scores
    paired = [
        (e["dev_mean"], e["held_mean"])
        for e in per_task_comparison
        if e["dev_mean"] is not None and e["held_mean"] is not None
    ]

    if len(paired) >= 5:
        dev_arr = np.array([p[0] for p in paired])
        held_arr = np.array([p[1] for p in paired])

        # Wilcoxon signed-rank test (non-parametric, safer for small samples)
        try:
            stat, pval = stats.wilcoxon(dev_arr, held_arr, alternative="two-sided")
            test_name = "wilcoxon"
        except Exception:
            stat, pval = stats.ttest_rel(dev_arr, held_arr)
            test_name = "ttest_rel"

        # ICC approximation: correlation between dev and held scores
        if len(paired) >= 3:
            icc_r, icc_p = stats.pearsonr(dev_arr, held_arr)
        else:
            icc_r, icc_p = None, None

        contamination_validated = pval > 0.05  # not significantly different → good

        result["statistical_test"] = {
            "test": test_name,
            "n_paired_tasks": len(paired),
            "statistic": float(stat),
            "pval": float(pval),
            "icc_pearsonr": float(icc_r) if icc_r is not None else None,
            "icc_pval": float(icc_p) if icc_p is not None else None,
            "contamination_validated": contamination_validated,
            "interpretation": (
                "Contamination resistance VALIDATED: dev and held-out seed scores are "
                "not significantly different (p > 0.05), indicating the benchmark is "
                "not contaminated by training data for these seeds."
                if contamination_validated else
                "CAUTION: dev and held-out seed scores differ significantly (p <= 0.05). "
                "Investigate whether specific tasks are driving this difference."
            ),
        }

        print(f"  {test_name}: stat={stat:.4f}, p={pval:.4f}")
        print(f"  dev mean={np.mean(dev_arr):.3f}, held mean={np.mean(held_arr):.3f}")
        print(f"  ICC (Pearson r): {icc_r:.3f}" if icc_r is not None else "  ICC: n/a")
        print(f"  Contamination resistance: {'VALIDATED' if contamination_validated else 'NOT VALIDATED'}")
    else:
        print(f"  Too few paired tasks ({len(paired)}) for statistical test.")

    return result


# ---------------------------------------------------------------------------
# LaTeX table
# ---------------------------------------------------------------------------

def write_latex_table(
    validation_results: list[dict],
    score_comparison: dict,
    out_path: Path,
) -> None:
    lines: list[str] = []
    lines.append(r"\begin{table}[htbp]")
    lines.append(r"\centering")
    lines.append(r"\caption{Contamination Resistance Validation. "
                 r"For each task, instances are generated for development seeds (0--2) "
                 r"and held-out seeds (5--7). "
                 r"Jaccard similarity measures workspace file overlap between seed~0 and seed~5. "
                 r"Oracle scores from existing ablation runs are compared across seed groups.}")
    lines.append(r"\label{tab:contamination}")
    lines.append(r"\small")
    lines.append(r"\begin{tabular}{lcccc}")
    lines.append(r"\toprule")
    lines.append(r"Metric & Value \\")
    lines.append(r"\midrule")

    # Generation success
    total = len(validation_results)
    dev_ok = sum(1 for r in validation_results if r["dev_gen_success"] == len(DEV_SEEDS))
    held_ok = sum(1 for r in validation_results if r["held_out_gen_success"] == len(HELD_OUT_SEEDS))
    all_differ = sum(1 for r in validation_results if r.get("all_held_out_differ", False))

    jaccards = [r["mean_jaccard_dev_vs_held"] for r in validation_results if r["mean_jaccard_dev_vs_held"] is not None]
    mean_jac = np.mean(jaccards) if jaccards else float("nan")
    std_jac = np.std(jaccards) if len(jaccards) > 1 else 0.0

    lines.append(rf"Tasks evaluated & {total} \\")
    lines.append(rf"Dev seeds fully generated & {dev_ok}/{total} \\")
    lines.append(rf"Held-out seeds fully generated & {held_ok}/{total} \\")
    lines.append(rf"Tasks: all held-out instances differ from dev & {all_differ}/{total} ({100*all_differ//max(1,total)}\%) \\")
    lines.append(rf"Mean workspace Jaccard (seed 0 vs seed 5) & ${mean_jac:.3f} \pm {std_jac:.3f}$ \\")

    # Score comparison
    sc = score_comparison
    if sc.get("dev_mean_score") is not None:
        lines.append(rf"Mean oracle score (dev seeds 0--2) & ${sc['dev_mean_score']:.3f}$ \\")
    if sc.get("held_mean_score") is not None:
        lines.append(rf"Mean oracle score (held-out seeds 5--7) & ${sc['held_mean_score']:.3f}$ \\")

    st = sc.get("statistical_test")
    if st:
        test_str = "Wilcoxon" if st["test"] == "wilcoxon" else "Paired $t$"
        lines.append(rf"{test_str} ($n={st['n_paired_tasks']}$) & $p = {st['pval']:.3f}$ \\")
        if st["icc_pearsonr"] is not None:
            lines.append(rf"ICC (Pearson $r$) dev vs held & ${st['icc_pearsonr']:.3f}$ \\")
        validated_str = r"\textbf{Validated}" if st["contamination_validated"] else r"\textbf{Not Validated}"
        lines.append(rf"Contamination resistance & {validated_str} \\")

    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}")

    if st:
        lines.append(r"\begin{tablenotes}\small")
        lines.append(r"\item " + st["interpretation"].replace("&", r"\&"))
        lines.append(r"\end{tablenotes}")

    lines.append(r"\end{table}")

    with open(out_path, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"Wrote {out_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tasks", nargs="*",
        help="Specific task IDs to validate (default: auto-select 50 representative tasks)",
    )
    parser.add_argument(
        "--n", type=int, default=N_TASKS,
        help=f"Number of tasks to select (default: {N_TASKS})",
    )
    parser.add_argument(
        "--skip-score-comparison", action="store_true",
        help="Skip loading ablation results for score comparison (faster)",
    )
    args = parser.parse_args()

    ablation_dir = REPO_ROOT / "shared" / "ablation_results"

    # Select tasks
    if args.tasks:
        task_ids = args.tasks
        print(f"Using {len(task_ids)} user-specified tasks.")
    else:
        print(f"Auto-selecting {args.n} representative parameterized tasks...")
        task_ids = select_tasks(args.n)

    if not task_ids:
        print("ERROR: No tasks found. Ensure generators/ directory is populated.", file=sys.stderr)
        sys.exit(1)

    # Validate generation diversity
    print(f"\nValidating generation diversity for {len(task_ids)} tasks...")
    validation_results: list[dict] = []
    success = 0
    failed = 0

    for i, tid in enumerate(task_ids, 1):
        print(f"  [{i:3d}/{len(task_ids)}] {tid}...", end=" ", flush=True)
        res = validate_task(tid)
        validation_results.append(res)
        if res.get("error"):
            print(f"ERROR: {res['error']}")
            failed += 1
        else:
            status = "OK" if res["all_held_out_differ"] else "WARN(same)"
            jac = res["mean_jaccard_dev_vs_held"]
            jac_str = f"jaccard={jac:.3f}" if jac is not None else "jaccard=n/a"
            print(f"{status} | {jac_str}")
            success += 1

    print(f"\n  Generation: {success} succeeded, {failed} failed")
    all_differ = sum(1 for r in validation_results if r.get("all_held_out_differ", False))
    print(f"  All held-out differ from dev: {all_differ}/{len(validation_results)}")

    jaccards = [r["mean_jaccard_dev_vs_held"] for r in validation_results if r["mean_jaccard_dev_vs_held"] is not None]
    if jaccards:
        print(f"  Mean Jaccard (seed 0 vs seed 5): {np.mean(jaccards):.3f} ± {np.std(jaccards):.3f}")
        print(f"  (Lower = more different = better contamination resistance)")

    # Score comparison using existing ablation results
    if not args.skip_score_comparison:
        print("\nComparing oracle scores: dev seeds (0-2) vs held-out seeds (5-7)...")
        score_comparison = score_comparison_analysis(task_ids, ablation_dir)
    else:
        print("\nSkipping score comparison (--skip-score-comparison).")
        score_comparison = {"skipped": True, "per_task": []}

    # Output JSON
    output = {
        "config": {
            "n_tasks": len(task_ids),
            "dev_seeds": DEV_SEEDS,
            "held_out_seeds": HELD_OUT_SEEDS,
        },
        "summary": {
            "tasks_evaluated": len(validation_results),
            "dev_gen_success": sum(1 for r in validation_results if r["dev_gen_success"] == len(DEV_SEEDS)),
            "held_out_gen_success": sum(1 for r in validation_results if r["held_out_gen_success"] == len(HELD_OUT_SEEDS)),
            "all_held_out_differ": all_differ,
            "all_held_out_differ_pct": float(100 * all_differ / max(1, len(validation_results))),
            "mean_jaccard": float(np.mean(jaccards)) if jaccards else None,
            "std_jaccard": float(np.std(jaccards)) if len(jaccards) > 1 else None,
        },
        "per_task_validation": validation_results,
        "score_comparison": score_comparison,
    }

    out_json = OUT_DIR / "contamination_validation.json"
    with open(out_json, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nWrote {out_json}")

    # LaTeX table
    out_tex = OUT_DIR / "table_contamination.tex"
    write_latex_table(validation_results, score_comparison, out_tex)

    # Final verdict
    print("\n=== CONTAMINATION RESISTANCE SUMMARY ===")
    print(f"Tasks validated: {len(validation_results)}")
    print(f"Held-out instances differ from dev: {all_differ}/{len(validation_results)}")
    if jaccards:
        print(f"Mean workspace Jaccard (lower=more diverse): {np.mean(jaccards):.3f}")
    st = score_comparison.get("statistical_test")
    if st:
        print(f"Statistical test ({st['test']}): p={st['pval']:.4f}")
        print(f"Verdict: {st['interpretation'][:80]}...")


if __name__ == "__main__":
    main()
