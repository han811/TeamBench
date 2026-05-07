#!/usr/bin/env python3
"""
Run evaluation on hidden-seed task instances.

Loads instances from tasks_hidden/{task_id}_seed{N}/ and runs the specified
ablation conditions, then grades results and writes scores to
shared/hidden_results/{model}_{condition}_{seeds}.json.

Hidden seed content (workspace files, expected.json) is NEVER included
in the output — only scores and metadata are written.

Usage:
    python scripts/evaluate_hidden.py --model gpt-5-mini --seeds 3 4 5
    python scripts/evaluate_hidden.py --model gpt-5-mini --seeds 3 4 5 --condition oracle full
    python scripts/evaluate_hidden.py --model gemini-3-flash-preview --seeds 3 --tasks D1_schema_drift
    python scripts/evaluate_hidden.py --list-instances
    python scripts/evaluate_hidden.py --dry-run --model gpt-5-mini --seeds 3 4
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

TASKS_HIDDEN_DIR = REPO_ROOT / "tasks_hidden"
HIDDEN_RESULTS_DIR = REPO_ROOT / "shared" / "hidden_results"
RUNS_DIR = REPO_ROOT / "shared" / "hidden_runs"

VALID_CONDITIONS = ["oracle", "restricted", "team_no_verify", "team_no_plan", "full"]
DEFAULT_CONDITIONS = ["oracle", "full"]
DEFAULT_SEEDS = [3, 4, 5]


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def discover_hidden_instances(
    hidden_dir: Path,
    seeds: list[int],
    tasks: Optional[list[str]] = None,
) -> list[dict]:
    """
    Discover available hidden instances in hidden_dir.

    Returns list of dicts with keys: task_id, seed, instance_dir
    """
    instances = []
    if not hidden_dir.exists():
        return instances

    for entry in sorted(hidden_dir.iterdir()):
        if not entry.is_dir():
            continue
        meta_path = entry / "hidden_meta.json"
        if not meta_path.exists():
            continue
        try:
            meta = json.loads(meta_path.read_text())
        except (json.JSONDecodeError, OSError):
            continue

        task_id = meta.get("task_id", "")
        seed = meta.get("seed")

        if seed not in seeds:
            continue
        if tasks and task_id not in tasks:
            continue

        instances.append({
            "task_id": task_id,
            "seed": seed,
            "instance_dir": str(entry),
            "category": meta.get("category", ""),
        })

    return instances


def stage_hidden_run(instance: dict, runs_dir: Path) -> tuple[str, str]:
    """
    Stage a run directory from a hidden instance.

    Copies workspace and reports from the hidden instance into a temporary
    run directory under runs_dir. Returns (run_id, run_dir).
    """
    task_id = instance["task_id"]
    seed = instance["seed"]
    instance_dir = Path(instance["instance_dir"])

    run_id = f"{now_utc()}_{uuid.uuid4().hex[:8]}"
    run_dir = runs_dir / task_id / f"seed{seed}" / run_id

    workspace_dst = run_dir / "workspace"
    reports_dst = run_dir / "reports"
    messages_dst = run_dir / "messages"
    submission_dst = run_dir / "submission"

    for d in [workspace_dst, reports_dst, messages_dst, submission_dst]:
        d.mkdir(parents=True, exist_ok=True)

    # Copy workspace files
    workspace_src = instance_dir / "workspace"
    if workspace_src.exists():
        shutil.copytree(workspace_src, workspace_dst, dirs_exist_ok=True)

    # Copy expected.json (grader needs it)
    expected_src = instance_dir / "reports" / "expected.json"
    if expected_src.exists():
        shutil.copy2(expected_src, reports_dst / "expected.json")

    # Write run metadata (does not include hidden content)
    meta = {
        "task_id": task_id,
        "seed": seed,
        "run_id": run_id,
        "hidden": True,
    }
    (run_dir / "run_meta.json").write_text(json.dumps(meta, indent=2))

    return run_id, str(run_dir)


def get_spec_path(instance: dict) -> str:
    """Return path to spec.md for this hidden instance."""
    return str(Path(instance["instance_dir"]) / "spec.md")


def run_condition(
    task_id: str,
    seed: int,
    condition: str,
    run_dir: str,
    instance_dir: str,
    model: str,
    max_turns: int,
    dry_run: bool,
) -> dict:
    """
    Execute one ablation condition for a task instance.

    Returns score dict with keys: pass, partial, condition, elapsed_sec, error
    """
    if dry_run:
        return {
            "pass": False,
            "partial": 0.0,
            "condition": condition,
            "elapsed_sec": 0.0,
            "error": "dry-run: skipped",
        }

    import time

    from harness.ablation import AblationCondition, run_ablation_condition
    from harness.run_all import grade_run

    run_dir_p = Path(run_dir)
    workspace_dir = str(run_dir_p / "workspace")
    reports_dir = str(run_dir_p / "reports")
    messages_dir = str(run_dir_p / "messages")
    submission_dir = str(run_dir_p / "submission")
    spec_path = str(Path(instance_dir) / "spec.md")
    brief_path = str(Path(instance_dir) / "brief.md")

    # Use the original task_dir from tasks/ for grade.sh (grader lives there)
    task_dir = str(REPO_ROOT / "tasks" / task_id)

    t0 = time.time()
    error: Optional[str] = None

    try:
        cond_enum = AblationCondition(condition)
        run_ablation_condition(
            condition=cond_enum,
            task_id=task_id,
            spec_path=spec_path,
            brief_path=brief_path,
            workspace_dir=workspace_dir,
            reports_dir=reports_dir,
            messages_dir=messages_dir,
            submission_dir=submission_dir,
            task_dir=task_dir,
            model=model,
            max_turns=max_turns,
        )
    except Exception as e:
        error = str(e)

    elapsed = time.time() - t0

    # Grade the run
    score = grade_run(task_id, task_dir, run_dir)
    score["condition"] = condition
    score["elapsed_sec"] = round(elapsed, 1)
    if error:
        score["error"] = error

    return score


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--model",
        default="gpt-5-mini",
        help="Model identifier to use (default: gpt-5-mini)",
    )
    parser.add_argument(
        "--seeds",
        nargs="+",
        type=int,
        default=DEFAULT_SEEDS,
        help=f"Hidden seeds to evaluate (default: {DEFAULT_SEEDS})",
    )
    parser.add_argument(
        "--condition",
        nargs="+",
        default=DEFAULT_CONDITIONS,
        choices=VALID_CONDITIONS,
        dest="conditions",
        help=f"Ablation conditions (default: {DEFAULT_CONDITIONS})",
    )
    parser.add_argument(
        "--tasks",
        nargs="+",
        default=None,
        help="Restrict to specific task_ids (default: all discovered instances)",
    )
    parser.add_argument(
        "--hidden-dir",
        default=str(TASKS_HIDDEN_DIR),
        help=f"Hidden instances directory (default: {TASKS_HIDDEN_DIR})",
    )
    parser.add_argument(
        "--out-dir",
        default=str(HIDDEN_RESULTS_DIR),
        help=f"Output directory for results (default: {HIDDEN_RESULTS_DIR})",
    )
    parser.add_argument(
        "--runs-dir",
        default=str(RUNS_DIR),
        help=f"Scratch directory for run staging (default: {RUNS_DIR})",
    )
    parser.add_argument(
        "--max-turns",
        type=int,
        default=40,
        help="Max agent turns per condition (default: 40)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Discover instances and print plan without running agents",
    )
    parser.add_argument(
        "--list-instances",
        action="store_true",
        help="List available hidden instances and exit",
    )
    parser.add_argument(
        "--keep-runs",
        action="store_true",
        help="Keep run directories after grading (default: delete)",
    )
    args = parser.parse_args()

    hidden_dir = Path(args.hidden_dir)
    out_dir = Path(args.out_dir)
    runs_dir = Path(args.runs_dir)

    # -- Discover instances -------------------------------------------------
    instances = discover_hidden_instances(hidden_dir, args.seeds, args.tasks)

    if args.list_instances:
        if not instances:
            print(f"No hidden instances found in {hidden_dir}")
            print("Run scripts/generate_hidden_seeds.py first.")
            return
        print(f"Found {len(instances)} hidden instances in {hidden_dir}:")
        for inst in instances:
            print(f"  {inst['task_id']}_seed{inst['seed']}  [{inst['category']}]")
        return

    if not instances:
        print(f"No hidden instances found in {hidden_dir} for seeds {args.seeds}.")
        print("Run scripts/generate_hidden_seeds.py first.")
        sys.exit(1)

    total_runs = len(instances) * len(args.conditions)
    print(f"Evaluating {len(instances)} instances × {len(args.conditions)} conditions "
          f"= {total_runs} runs")
    print(f"Model: {args.model}  Seeds: {args.seeds}  Conditions: {args.conditions}")

    if args.dry_run:
        for inst in instances:
            print(f"  [dry-run] {inst['task_id']}_seed{inst['seed']} × {args.conditions}")
        return

    # -- Run evaluation -----------------------------------------------------
    out_dir.mkdir(parents=True, exist_ok=True)
    runs_dir.mkdir(parents=True, exist_ok=True)

    seeds_str = "_".join(str(s) for s in sorted(set(args.seeds)))
    conds_str = "_".join(sorted(args.conditions))
    out_file = out_dir / f"{args.model}_{conds_str}_seeds{seeds_str}.json"

    all_results: list[dict] = []
    done = 0

    for inst in instances:
        task_id = inst["task_id"]
        seed = inst["seed"]

        # Stage run directory
        run_id, run_dir = stage_hidden_run(inst, runs_dir)

        task_results: dict = {
            "task_id": task_id,
            "seed": seed,
            "category": inst["category"],
            "model": args.model,
            "run_id": run_id,
            "conditions": {},
        }

        for condition in args.conditions:
            done += 1
            print(f"  [{done:4d}/{total_runs}] {task_id}_seed{seed} / {condition} ...", end="", flush=True)

            score = run_condition(
                task_id=task_id,
                seed=seed,
                condition=condition,
                run_dir=run_dir,
                instance_dir=inst["instance_dir"],
                model=args.model,
                max_turns=args.max_turns,
                dry_run=args.dry_run,
            )

            # Strip any fields that could leak hidden content
            safe_score = {
                k: v for k, v in score.items()
                if k not in ("workspace", "expected", "spec", "brief")
            }
            task_results["conditions"][condition] = safe_score

            passed = safe_score.get("pass", False)
            partial = safe_score.get("partial", 0.0)
            print(f" {'PASS' if passed else 'FAIL'} (partial={partial:.2f})")

        all_results.append(task_results)

        # Clean up run directory to avoid storing hidden content on disk
        if not args.keep_runs:
            shutil.rmtree(run_dir, ignore_errors=True)

        # Checkpoint after each task
        _write_results(all_results, args.model, args.seeds, args.conditions, out_file)

    # -- Final output -------------------------------------------------------
    _write_results(all_results, args.model, args.seeds, args.conditions, out_file)

    n_pass = sum(
        1
        for r in all_results
        for cond, s in r["conditions"].items()
        if s.get("pass")
    )
    print(f"\nDone. {n_pass}/{total_runs} runs passed.")
    print(f"Results written to {out_file}")


def _write_results(
    results: list[dict],
    model: str,
    seeds: list[int],
    conditions: list[str],
    out_file: Path,
) -> None:
    """Write results JSON, excluding any hidden content fields."""
    output = {
        "model": model,
        "seeds": seeds,
        "conditions": conditions,
        "generated_at": now_utc(),
        "note": (
            "Hidden track results. Workspace content and expected values "
            "are not included. Task IDs and scores only."
        ),
        "results": results,
    }
    out_file.write_text(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
