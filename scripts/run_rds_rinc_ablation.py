#!/usr/bin/env python3
"""Ablation study for RDS* and RINC* tasks (real-data and real-incident archetypes).

Hypothesis: different task archetypes produce different TNI patterns.
  - adversarial (RDS11-18): highest TNI
  - synthesis   (RDS25-30): high TNI
  - discovery   (RDS19-24): variable TNI
  - open_ended  (RDS1-10):  moderate TNI
  - incident    (RINC*):    incident-specific pattern

Archetype classification by task_id prefix number:
  RDS1-RDS10  -> open_ended
  RDS11-RDS18 -> adversarial
  RDS19-RDS24 -> discovery
  RDS25-RDS30 -> synthesis
  RINC*       -> incident

Usage:
    python scripts/run_rds_rinc_ablation.py --dry-run
    python scripts/run_rds_rinc_ablation.py
    python scripts/run_rds_rinc_ablation.py --model gpt-5-mini --seeds 0 1 2
    python scripts/run_rds_rinc_ablation.py --batch 1   # tasks 0-19
    python scripts/run_rds_rinc_ablation.py --batch 2   # tasks 20+
    python scripts/run_rds_rinc_ablation.py --resume    # skip already-completed runs
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from collections import defaultdict

# Ensure repo root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from harness.ablation import run_full_ablation, AblationCondition
from harness.run_all import discover_tasks

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_MODEL = "gemini-3-flash-preview"

CONDITIONS = [
    AblationCondition.ORACLE,
    AblationCondition.RESTRICTED,
    AblationCondition.TEAM_NO_PLAN,
    AblationCondition.TEAM_NO_VERIFY,
    AblationCondition.FULL,
]

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ---------------------------------------------------------------------------
# .env loader (does not overwrite existing env vars)
# ---------------------------------------------------------------------------

def _load_dotenv() -> None:
    env_path = os.path.join(REPO_ROOT, ".env")
    if not os.path.isfile(env_path):
        return
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip())


# ---------------------------------------------------------------------------
# Archetype classification
# ---------------------------------------------------------------------------

def classify_archetype(task_id: str) -> str:
    """Return archetype string for a task_id.

    task_id may include a seed suffix like RDS11_survivorship_bias_seed0;
    we parse only the numeric part after the prefix.
    """
    m = re.match(r"^(RDS|RINC)(\d+)", task_id)
    if m is None:
        return "unknown"
    prefix = m.group(1)
    num = int(m.group(2))
    if prefix == "RINC":
        return "incident"
    # RDS
    if 1 <= num <= 10:
        return "open_ended"
    if 11 <= num <= 18:
        return "adversarial"
    if 19 <= num <= 24:
        return "discovery"
    if 25 <= num <= 30:
        return "synthesis"
    return "open_ended"  # fallback for any RDS31+


# ---------------------------------------------------------------------------
# Resume helper
# ---------------------------------------------------------------------------

def _load_existing_runs(output_path: str) -> set[tuple[str, str, int]]:
    """Return set of (task_id, condition, seed) already present in output file."""
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


# ---------------------------------------------------------------------------
# Post-run archetype analysis
# ---------------------------------------------------------------------------

def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def compute_archetype_analysis(runs: list[dict]) -> dict:
    """Compute per-archetype TNI, team uplift, planning value, verification value."""
    # Group partial scores by (archetype, condition)
    arch_cond: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))

    for run in runs:
        task_id = run.get("task_id", "")
        cond = run.get("condition", "")
        ps = run.get("partial_score")
        if ps is None:
            ps = 1.0 if run.get("pass") else 0.0
        arch = classify_archetype(task_id)
        arch_cond[arch][cond].append(float(ps))

    eps = 1e-6
    results: dict[str, dict] = {}

    for arch, cond_scores in arch_cond.items():
        s_oracle = _mean(cond_scores.get("oracle", []))
        s_restricted = _mean(cond_scores.get("restricted", []))
        s_full = _mean(cond_scores.get("full", []))
        s_no_plan = _mean(cond_scores.get("team_no_plan", []))
        s_no_verify = _mean(cond_scores.get("team_no_verify", []))

        tni = (s_full - s_restricted) / max(eps, s_oracle - s_restricted)
        team_uplift = s_full - s_oracle
        planning_value = s_full - s_no_plan
        verification_value = s_full - s_no_verify

        n_tasks = len({r.get("task_id") for r in runs if classify_archetype(r.get("task_id", "")) == arch})

        results[arch] = {
            "n_tasks": n_tasks,
            "oracle": round(s_oracle, 4),
            "restricted": round(s_restricted, 4),
            "full": round(s_full, 4),
            "team_no_plan": round(s_no_plan, 4),
            "team_no_verify": round(s_no_verify, 4),
            "tni": round(tni, 4),
            "team_uplift": round(team_uplift, 4),
            "planning_value": round(planning_value, 4),
            "verification_value": round(verification_value, 4),
        }

    return results


def print_archetype_table(arch_results: dict) -> None:
    """Print per-archetype results table to stdout."""
    archetypes = ["adversarial", "synthesis", "discovery", "open_ended", "incident", "unknown"]
    print("\n" + "=" * 80)
    print("PER-ARCHETYPE RESULTS")
    print("=" * 80)
    header = f"  {'Archetype':<14} {'N':>4}  {'Oracle':>7}  {'Full':>7}  {'TNI':>7}  {'Uplift':>8}  {'PlanVal':>8}  {'VerVal':>8}"
    print(header)
    print("  " + "-" * 76)

    for arch in archetypes:
        if arch not in arch_results:
            continue
        r = arch_results[arch]
        print(
            f"  {arch:<14} {r['n_tasks']:>4}  "
            f"{r['oracle']:>7.3f}  {r['full']:>7.3f}  "
            f"{r['tni']:>7.4f}  {r['team_uplift']:>+8.3f}  "
            f"{r['planning_value']:>+8.3f}  {r['verification_value']:>+8.3f}"
        )

    print("=" * 80)

    # Hypothesis check
    print("\nHYPOTHESIS: adversarial TNI > other archetypes")
    adv_tni = arch_results.get("adversarial", {}).get("tni")
    if adv_tni is not None:
        others = {k: v["tni"] for k, v in arch_results.items() if k != "adversarial" and k != "unknown"}
        if others:
            max_other_arch = max(others, key=lambda k: others[k])
            max_other_tni = others[max_other_arch]
            if adv_tni > max_other_tni:
                print(f"  SUPPORTED: adversarial TNI={adv_tni:.4f} > {max_other_arch} TNI={max_other_tni:.4f}")
            else:
                print(f"  NOT SUPPORTED: adversarial TNI={adv_tni:.4f}, highest other={max_other_arch} TNI={max_other_tni:.4f}")
        else:
            print(f"  adversarial TNI={adv_tni:.4f} (no other archetypes to compare)")
    else:
        print("  No adversarial results available yet.")


def print_per_task_table(runs: list[dict]) -> None:
    """Print per-task pass/partial score breakdown."""
    task_cond: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for run in runs:
        task_id = run.get("task_id", "")
        cond = run.get("condition", "")
        ps = run.get("partial_score")
        if ps is None:
            ps = 1.0 if run.get("pass") else 0.0
        task_cond[task_id][cond].append(float(ps))

    print("\n" + "=" * 90)
    print("PER-TASK RESULTS")
    print("=" * 90)
    cond_names = ["oracle", "restricted", "team_no_plan", "team_no_verify", "full"]
    header = f"  {'Task':<40} {'Arch':<12} " + "  ".join(f"{c[:7]:>7}" for c in cond_names)
    print(header)
    print("  " + "-" * 86)

    for task_id in sorted(task_cond.keys()):
        arch = classify_archetype(task_id)
        scores = task_cond[task_id]
        row = f"  {task_id:<40} {arch:<12} "
        row += "  ".join(
            f"{_mean(scores.get(c, [])):.3f}" if c in scores else "  ---  "
            for c in cond_names
        )
        print(row)

    print("=" * 90)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    _load_dotenv()

    ap = argparse.ArgumentParser(
        description="Ablation study for RDS* and RINC* task archetypes",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument(
        "--model", default=DEFAULT_MODEL,
        help=f"Model to use (default: {DEFAULT_MODEL})",
    )
    ap.add_argument(
        "--seeds", nargs="+", type=int, default=[0],
        help="Seeds to run (default: 0)",
    )
    ap.add_argument(
        "--batch", type=int, default=0,
        help="Batch number (1=tasks 0-19, 2=tasks 20+). 0=all",
    )
    ap.add_argument(
        "--resume", action="store_true",
        help="Skip task/condition/seed combos already present in the output file",
    )
    ap.add_argument(
        "--dry-run", action="store_true",
        help="List tasks that would run without executing anything",
    )
    ap.add_argument(
        "--tasks-dir", default=os.path.join(REPO_ROOT, "tasks"),
        help="Tasks directory (default: tasks/)",
    )
    args = ap.parse_args()

    os.environ["PYTHONUNBUFFERED"] = "1"

    # Discover RDS* and RINC* tasks
    all_tasks = discover_tasks(args.tasks_dir)
    rds_rinc = sorted(
        t for t in all_tasks
        if re.match(r"^(RDS|RINC)\d+", t)
    )

    if not rds_rinc:
        print("ERROR: No RDS* or RINC* tasks found in tasks/", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(rds_rinc)} RDS/RINC tasks (from {len(all_tasks)} total)")

    # Batch splitting
    if args.batch == 1:
        tasks = rds_rinc[:20]
    elif args.batch == 2:
        tasks = rds_rinc[20:]
    else:
        tasks = rds_rinc

    # Build output path
    seed_str = "_".join(map(str, args.seeds))
    model_slug = args.model.replace("-", "_").replace(".", "")
    batch_suffix = f"_batch{args.batch}" if args.batch > 0 else ""
    outpath = os.path.join(
        REPO_ROOT, "shared", "ablation_results",
        f"rds_rinc_ablation_{model_slug}_seed{seed_str}{batch_suffix}.json",
    )

    # Resume: find already-completed runs
    skip_set: set[tuple[str, str, int]] = set()
    if args.resume:
        skip_set = _load_existing_runs(outpath)
        if skip_set:
            print(f"Resume: {len(skip_set)} runs already in {outpath}, will skip them")

    # Determine pending tasks
    total_runs = len(tasks) * len(CONDITIONS) * len(args.seeds)
    if args.resume and skip_set:
        pending_tasks = [
            t for t in tasks
            if any(
                (t, c.value, s) not in skip_set
                for c in CONDITIONS
                for s in args.seeds
            )
        ]
        skipped = sum(
            1 for t in tasks
            for c in CONDITIONS
            for s in args.seeds
            if (t, c.value, s) in skip_set
        )
        pending_runs = total_runs - skipped
    else:
        pending_tasks = tasks
        pending_runs = total_runs

    # Archetype breakdown
    arch_counts: dict[str, int] = defaultdict(int)
    for t in pending_tasks:
        arch_counts[classify_archetype(t)] += 1

    print(f"\nModel:      {args.model}")
    print(f"Seeds:      {args.seeds}")
    print(f"Conditions: {[c.value for c in CONDITIONS]}")
    print(f"Output:     {outpath}")
    print(f"Tasks:      {len(pending_tasks)} (of {len(tasks)})")
    print(f"Total runs: {pending_runs} (of {total_runs})")
    print(f"Archetype breakdown:")
    for arch in ["adversarial", "synthesis", "discovery", "open_ended", "incident", "unknown"]:
        if arch_counts.get(arch):
            print(f"  {arch:<14}: {arch_counts[arch]} tasks")

    if args.dry_run:
        print("\n[DRY RUN] Tasks that would be executed:")
        for i, t in enumerate(pending_tasks, 1):
            arch = classify_archetype(t)
            print(f"  {i:3d}. {t:<45} [{arch}]")
        print(
            f"\nTotal: {len(pending_tasks)} tasks x "
            f"{len(CONDITIONS)} conditions x "
            f"{len(args.seeds)} seed(s) = {pending_runs} runs"
        )
        return

    if not pending_tasks:
        print("\nAll runs already completed. Nothing to do.")
        return

    start_time = time.time()
    print(f"\nStarted at {time.strftime('%Y-%m-%d %H:%M:%S')}")

    run_full_ablation(
        model=args.model,
        tasks=pending_tasks,
        seeds=args.seeds,
        tasks_dir=args.tasks_dir,
        output=outpath,
        conditions=CONDITIONS,
    )

    elapsed = time.time() - start_time
    print(f"\nCompleted in {elapsed / 60:.1f}m")
    print(f"Results: {outpath}")

    # Post-run archetype analysis
    if os.path.isfile(outpath):
        with open(outpath, encoding="utf-8") as f:
            data = json.load(f)
        runs = data.get("runs", [])
        arch_results = compute_archetype_analysis(runs)
        print_archetype_table(arch_results)
        print_per_task_table(runs)


if __name__ == "__main__":
    main()
