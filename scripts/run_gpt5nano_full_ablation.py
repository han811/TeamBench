#!/usr/bin/env python3
"""Full 147+ task ablation with GPT-5-Nano (or GPT-5-Mini via --model flag).

Replicates the reference evaluation (Gemini 3 Flash) on a second model to
validate that team benefits generalize beyond the primary model.

Usage:
    python scripts/run_gpt5nano_full_ablation.py
    python scripts/run_gpt5nano_full_ablation.py --model gpt-5-mini
    python scripts/run_gpt5nano_full_ablation.py --batch 1   # tasks 0-49
    python scripts/run_gpt5nano_full_ablation.py --batch 2   # tasks 50-99
    python scripts/run_gpt5nano_full_ablation.py --batch 3   # tasks 100+
    python scripts/run_gpt5nano_full_ablation.py --resume    # skip already-completed tasks
    python scripts/run_gpt5nano_full_ablation.py --dry-run   # list tasks without running
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from harness.ablation import run_full_ablation, AblationCondition
from harness.run_all import discover_tasks

CONDITIONS = [
    AblationCondition.ORACLE,
    AblationCondition.RESTRICTED,
    AblationCondition.TEAM_NO_VERIFY,
    AblationCondition.TEAM_NO_PLAN,
    AblationCondition.FULL,
]

# Exclude EA tasks (require special orchestrator)
EXCLUDE_PREFIXES = ["EA"]

# Approximate cost per 1K tokens (input/output blended) in USD.
# These are rough estimates; update if pricing changes.
COST_PER_1K_TOKENS = {
    "gpt-5-nano": 0.00015,   # ~$0.15 / 1M tokens
    "gpt-5-mini": 0.00060,   # ~$0.60 / 1M tokens
}
# Rough estimate: ~4K tokens average per condition×task×seed run.
AVG_TOKENS_PER_RUN = 4000


def _load_existing_results(output_path: str) -> set[tuple[str, str, int]]:
    """Return set of (task_id, condition, seed) tuples already present in output."""
    if not os.path.isfile(output_path):
        return set()
    try:
        with open(output_path, encoding="utf-8") as f:
            data = json.load(f)
        done: set[tuple[str, str, int]] = set()
        for run in data.get("runs", []):
            tid = run.get("task_id", "")
            cond = run.get("condition", "")
            seed = run.get("seed", 0)
            if tid and cond:
                done.add((tid, cond, seed))
        return done
    except Exception:
        return set()


def _print_progress(
    completed: int,
    total: int,
    passed: int,
    start_time: float,
) -> None:
    elapsed = time.time() - start_time
    pct = completed / total * 100 if total > 0 else 0
    rate = completed / elapsed if elapsed > 0 else 0
    remaining = (total - completed) / rate if rate > 0 else float("inf")
    rem_str = f"{remaining / 60:.1f}m" if remaining < 3600 else f"{remaining / 3600:.1f}h"
    pass_rate = passed / completed * 100 if completed > 0 else 0
    print(
        f"  Progress: {completed}/{total} ({pct:.1f}%) | "
        f"Passed: {passed} ({pass_rate:.1f}%) | "
        f"ETA: {rem_str}"
    )


def _estimate_cost(model: str, n_runs: int) -> str:
    cpp = COST_PER_1K_TOKENS.get(model, COST_PER_1K_TOKENS["gpt-5-nano"])
    total_tokens = n_runs * AVG_TOKENS_PER_RUN
    cost = total_tokens / 1000 * cpp
    return f"~${cost:.2f} (est. {total_tokens:,} tokens @ ${cpp * 1000:.4f}/K)"


def _print_summary_table(output_path: str) -> None:
    """Print per-condition pass-rate summary from completed output file."""
    if not os.path.isfile(output_path):
        return
    try:
        with open(output_path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return

    runs = data.get("runs", [])
    if not runs:
        return

    cond_scores: dict[str, list[float]] = defaultdict(list)
    for run in runs:
        cond = run.get("condition", "")
        ps = run.get("partial_score")
        passed = run.get("passed")
        if cond and ps is not None:
            cond_scores[cond].append(float(ps))
        elif cond and passed is not None:
            cond_scores[cond].append(1.0 if passed else 0.0)

    if not cond_scores:
        return

    print("\n" + "=" * 55)
    print("Per-Condition Pass Rates")
    print("=" * 55)
    print(f"  {'Condition':<22s} {'N':>5s}  {'Pass Rate':>10s}  {'Avg Score':>10s}")
    print("  " + "-" * 51)

    cond_order = [c.value for c in CONDITIONS]
    for cond in cond_order:
        if cond not in cond_scores:
            continue
        scores = cond_scores[cond]
        n = len(scores)
        avg = sum(scores) / n
        passed_n = sum(1 for s in scores if s >= 1.0)
        pass_rate = passed_n / n * 100
        print(f"  {cond:<22s} {n:>5d}  {pass_rate:>9.1f}%  {avg:>10.3f}")

    all_scores = [s for ss in cond_scores.values() for s in ss]
    print("  " + "-" * 51)
    print(f"  {'TOTAL':<22s} {len(all_scores):>5d}")
    print("=" * 55)


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Full 147+ task ablation with GPT-5-Nano or GPT-5-Mini",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument(
        "--model",
        default="gpt-5-nano",
        choices=["gpt-5-nano", "gpt-5-mini"],
        help="Model to use (default: gpt-5-nano)",
    )
    ap.add_argument(
        "--batch", type=int, default=0,
        help="Batch number (1=tasks 0-49, 2=50-99, 3=100+). 0=all",
    )
    ap.add_argument(
        "--seeds", nargs="+", type=int, default=[0],
        help="Seeds to run (default: 0)",
    )
    ap.add_argument(
        "--resume", action="store_true",
        help="Skip task/condition/seed combos already present in the output file",
    )
    ap.add_argument(
        "--dry-run", action="store_true",
        help="List tasks that would run without executing anything",
    )
    args = ap.parse_args()

    # Discover and filter tasks
    all_tasks = discover_tasks("tasks")
    tasks = [t for t in all_tasks
             if not any(t.startswith(p) for p in EXCLUDE_PREFIXES)]

    print(f"Total tasks: {len(tasks)} (excluded {len(all_tasks) - len(tasks)} EA tasks)")

    # Batch splitting
    if args.batch == 1:
        tasks = tasks[:50]
    elif args.batch == 2:
        tasks = tasks[50:100]
    elif args.batch == 3:
        tasks = tasks[100:]

    batch_suffix = f"_batch{args.batch}" if args.batch > 0 else ""
    seed_str = "_".join(map(str, args.seeds))
    model_slug = args.model.replace("-", "").replace(".", "")
    outpath = os.path.join(
        "shared", "ablation_results",
        f"full_ablation_{model_slug}_seed{seed_str}{batch_suffix}.json"
    )

    # Resume: filter already-completed combos
    skip_set: set[tuple[str, str, int]] = set()
    if args.resume:
        skip_set = _load_existing_results(outpath)
        if skip_set:
            print(f"Resume: {len(skip_set)} runs already in {outpath}, will skip them")

    # Determine pending task list for display / dry-run
    total_runs = len(tasks) * len(CONDITIONS) * len(args.seeds)
    pending_tasks = tasks
    if args.resume and skip_set:
        pending_tasks = [
            t for t in tasks
            if any(
                (t, c.value, s) not in skip_set
                for c in CONDITIONS
                for s in args.seeds
            )
        ]
        skipped_runs = sum(
            1 for t in tasks
            for c in CONDITIONS
            for s in args.seeds
            if (t, c.value, s) in skip_set
        )
        pending_runs = total_runs - skipped_runs
    else:
        pending_runs = total_runs

    # Header
    print(f"Running batch {'all' if args.batch == 0 else args.batch}: "
          f"{len(pending_tasks)} tasks")
    print(f"Model:      {args.model}")
    print(f"Conditions: {[c.value for c in CONDITIONS]}")
    print(f"Seeds:      {args.seeds}")
    print(f"Output:     {outpath}")
    print(f"Total runs: {pending_runs} (of {total_runs})")
    print(f"Cost est.:  {_estimate_cost(args.model, pending_runs)}")

    if args.dry_run:
        print("\n[DRY RUN] Tasks that would be executed:")
        for i, t in enumerate(pending_tasks, 1):
            print(f"  {i:3d}. {t}")
        print(f"\nTotal: {len(pending_tasks)} tasks × "
              f"{len(CONDITIONS)} conditions × "
              f"{len(args.seeds)} seed(s) = {pending_runs} runs")
        return

    if not pending_tasks:
        print("\nAll runs already completed. Nothing to do.")
        _print_summary_table(outpath)
        return

    start_time = time.time()
    print(f"\nStarted at {time.strftime('%Y-%m-%d %H:%M:%S')}")

    # run_full_ablation handles its own progress printing; we wrap to add
    # our summary table afterwards.
    run_full_ablation(
        model=args.model,
        tasks=pending_tasks,
        seeds=args.seeds,
        tasks_dir="tasks",
        output=outpath,
        conditions=CONDITIONS,
    )

    elapsed = time.time() - start_time
    print(f"\nFinished in {elapsed / 60:.1f}m")
    print(f"Results saved to {outpath}")

    _print_summary_table(outpath)


if __name__ == "__main__":
    main()
