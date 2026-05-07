#!/usr/bin/env python3
"""
Generate hidden test set instances for the TeamBench leaderboard.

Selects 50 representative tasks across all categories (proportional to
category size) and generates instances for held-out seeds 3-9.

Output layout:
    tasks_hidden/{task_id}_seed{N}/
        workspace/        <- staged workspace files
        reports/          <- expected.json (grader-only, never published)
        spec.md           <- Planner-visible spec
        brief.md          <- Executor-visible brief
        task.yaml         <- task metadata

IMPORTANT: tasks_hidden/ is git-ignored and must never be committed.

Usage:
    python scripts/generate_hidden_seeds.py
    python scripts/generate_hidden_seeds.py --seeds 3 4 5
    python scripts/generate_hidden_seeds.py --tasks D1_schema_drift SEC1_input_validation
    python scripts/generate_hidden_seeds.py --dry-run
    python scripts/generate_hidden_seeds.py --validate-only
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

HIDDEN_SEEDS = [3, 4, 5, 6, 7, 8, 9]
N_TASKS = 50
TASKS_HIDDEN_DIR = REPO_ROOT / "tasks_hidden"
TASKS_DIR = REPO_ROOT / "tasks"

# Archetypes required for representative coverage
REQUIRED_ARCHETYPES = {"relay", "open_ended", "adversarial", "discovery", "synthesis"}

# Known tasks that must be included (RDS, RINC, and multi-language)
MUST_INCLUDE_PREFIXES = {"RDS", "RINC"}

# Categories and approximate target counts (proportional to category size in public tasks)
# Total 50 tasks across 19+ categories; GH/ML/DS/RDS get more slots due to larger size.
CATEGORY_QUOTAS: dict[str, int] = {
    "GH":      8,   # 650 tasks  -> ~8 slots
    "ML":      5,   # 150 tasks  -> ~5 slots
    "DS":      5,   # 147 tasks  -> ~5 slots
    "RDS":     4,   # 90 tasks   -> ~4 slots
    "RINC":    2,   # 30 tasks   -> ~2 slots
    "INC":     2,
    "D":       2,
    "MULTI":   2,
    "O":       1,
    "SEC":     2,
    "TEST":    2,
    "IR":      1,
    "P":       1,
    "TRAP":    2,
    "CROSS":   2,
    "LH":      1,
    "S":       1,
    "SPEC":    1,
    "CR":      1,
    "DIST":    1,
    "CRYPTO":  1,
    "NEG":     1,
    "EA":      1,
}
# Fallback: any remaining slots go to the largest unrepresented categories


def get_category(task_id: str) -> str:
    """Extract category prefix from task_id (e.g., 'D1_schema_drift' -> 'D')."""
    prefix = task_id.split("_")[0].rstrip("0123456789")
    return prefix


def list_parameterized_tasks() -> list[str]:
    """Return sorted list of task_ids that have a parameterized generator."""
    from generators.registry import has_generator

    task_ids = []
    for entry in sorted(os.listdir(TASKS_DIR)):
        task_path = TASKS_DIR / entry
        if task_path.is_dir() and (task_path / "task.yaml").exists():
            if has_generator(entry):
                task_ids.append(entry)
    return task_ids


def read_task_yaml(task_id: str) -> dict:
    """Read task.yaml for a task, returning parsed dict (best-effort)."""
    import re

    yaml_path = TASKS_DIR / task_id / "task.yaml"
    if not yaml_path.exists():
        return {}
    content = yaml_path.read_text()
    result: dict = {}
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r"^(\w+)\s*:\s*(.+)$", line)
        if m:
            key, val = m.group(1), m.group(2).strip()
            result[key] = val
    return result


def select_tasks(all_task_ids: list[str], n: int = N_TASKS) -> list[str]:
    """
    Select n representative tasks from all_task_ids.

    Strategy:
    1. Group tasks by category.
    2. Fill quotas from CATEGORY_QUOTAS (sample deterministically — sort + modular pick).
    3. Add must-include prefixes.
    4. Top up remaining slots from largest categories.
    5. Return exactly n tasks (or all available if fewer exist).
    """
    by_category: dict[str, list[str]] = defaultdict(list)
    for tid in all_task_ids:
        cat = get_category(tid)
        by_category[cat].append(tid)

    selected: list[str] = []
    used: set[str] = set()

    def pick(candidates: list[str], k: int) -> list[str]:
        """Pick k items deterministically (evenly spaced by sorted index)."""
        if not candidates or k <= 0:
            return []
        if len(candidates) <= k:
            return list(candidates)
        step = len(candidates) / k
        indices = [int(i * step) for i in range(k)]
        return [candidates[i] for i in indices]

    # Step 1: fill category quotas
    for cat, quota in CATEGORY_QUOTAS.items():
        available = [t for t in sorted(by_category.get(cat, [])) if t not in used]
        chosen = pick(available, quota)
        for t in chosen:
            used.add(t)
            selected.append(t)

    # Step 2: ensure must-include prefixes have at least one representative
    for prefix in MUST_INCLUDE_PREFIXES:
        if not any(get_category(t) == prefix for t in selected):
            candidates = [t for t in sorted(by_category.get(prefix, [])) if t not in used]
            if candidates:
                selected.append(candidates[0])
                used.add(candidates[0])

    # Step 3: top up to n from remaining categories (largest first)
    remaining_needed = n - len(selected)
    if remaining_needed > 0:
        all_remaining = [t for t in all_task_ids if t not in used]
        # Sort by category size (desc) then task_id for determinism
        all_remaining.sort(key=lambda t: (-len(by_category[get_category(t)]), t))
        for t in all_remaining[:remaining_needed]:
            selected.append(t)
            used.add(t)

    return sorted(selected)[:n]


def validate_instance(
    task_id: str,
    seed: int,
    out_dir: Path,
) -> dict:
    """
    Validate a generated instance on disk.

    Checks:
    - spec.md exists and is non-empty
    - brief.md exists and is non-empty
    - workspace/ is non-empty
    - reports/expected.json is valid JSON with at least one key

    Returns dict with keys: ok (bool), errors (list[str])
    """
    errors: list[str] = []

    spec_path = out_dir / "spec.md"
    if not spec_path.exists() or not spec_path.read_text().strip():
        errors.append("spec.md missing or empty")

    brief_path = out_dir / "brief.md"
    if not brief_path.exists() or not brief_path.read_text().strip():
        errors.append("brief.md missing or empty")

    workspace_dir = out_dir / "workspace"
    if not workspace_dir.exists() or not any(workspace_dir.iterdir()):
        errors.append("workspace/ missing or empty")

    expected_path = out_dir / "reports" / "expected.json"
    if not expected_path.exists():
        errors.append("reports/expected.json missing")
    else:
        try:
            data = json.loads(expected_path.read_text())
            if not data:
                errors.append("reports/expected.json is empty dict")
        except json.JSONDecodeError as e:
            errors.append(f"reports/expected.json invalid JSON: {e}")

    return {"ok": len(errors) == 0, "errors": errors}


def validate_cross_seed_diversity(task_id: str, hidden_seed: int) -> dict:
    """
    Validate that a hidden seed produces a different instance than seed 0.

    Uses the generator's validate_cross_seed() method.
    Returns dict with keys: ok (bool), error (str or None)
    """
    from generators.registry import get_generator

    try:
        gen = get_generator(task_id)
        diverse = gen.validate_cross_seed(0, hidden_seed)
        if diverse:
            return {"ok": True, "error": None}
        else:
            return {
                "ok": False,
                "error": f"seed {hidden_seed} produces same output as seed 0",
            }
    except Exception as e:
        return {"ok": False, "error": f"cross-seed check error: {e}"}


def generate_instance(
    task_id: str,
    seed: int,
    out_base: Path,
    dry_run: bool = False,
) -> dict:
    """
    Generate and write one hidden instance to out_base/{task_id}_seed{seed}/.

    Returns result dict with keys:
        task_id, seed, out_dir, ok, validation, cross_seed, error
    """
    from generators.registry import get_generator

    instance_dir = out_base / f"{task_id}_seed{seed}"
    workspace_dir = instance_dir / "workspace"
    reports_dir = instance_dir / "reports"

    result: dict = {
        "task_id": task_id,
        "seed": seed,
        "out_dir": str(instance_dir),
        "ok": False,
        "validation": None,
        "cross_seed": None,
        "error": None,
    }

    if dry_run:
        result["ok"] = True
        result["error"] = "dry-run: skipped"
        return result

    try:
        gen = get_generator(task_id)
        generated = gen.generate(seed=seed)

        gen.write_to_disk(
            generated,
            workspace_dir=str(workspace_dir),
            reports_dir=str(reports_dir),
            task_dir=str(instance_dir),
        )

        # Write task.yaml copy so evaluate_hidden.py can discover instances
        src_yaml = TASKS_DIR / task_id / "task.yaml"
        if src_yaml.exists():
            import shutil
            shutil.copy2(src_yaml, instance_dir / "task.yaml")

        # Write hidden_meta.json
        meta = {
            "task_id": task_id,
            "seed": seed,
            "hidden": True,
            "category": get_category(task_id),
        }
        (instance_dir / "hidden_meta.json").write_text(
            json.dumps(meta, indent=2)
        )

    except Exception as e:
        result["error"] = str(e)
        return result

    # Validate the instance
    validation = validate_instance(task_id, seed, instance_dir)
    result["validation"] = validation

    # Cross-seed diversity check
    cross_seed = validate_cross_seed_diversity(task_id, seed)
    result["cross_seed"] = cross_seed

    result["ok"] = validation["ok"] and cross_seed["ok"]
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--seeds",
        nargs="+",
        type=int,
        default=HIDDEN_SEEDS,
        help=f"Hidden seeds to generate (default: {HIDDEN_SEEDS})",
    )
    parser.add_argument(
        "--tasks",
        nargs="+",
        default=None,
        help="Explicit task list (default: auto-select 50 representative tasks)",
    )
    parser.add_argument(
        "--n-tasks",
        type=int,
        default=N_TASKS,
        help=f"Number of tasks to select (default: {N_TASKS})",
    )
    parser.add_argument(
        "--out-dir",
        default=str(TASKS_HIDDEN_DIR),
        help=f"Output directory (default: {TASKS_HIDDEN_DIR})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print selected tasks and seeds without generating files",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate existing instances in out-dir without regenerating",
    )
    parser.add_argument(
        "--summary-out",
        default=None,
        help="Write JSON summary to this path",
    )
    args = parser.parse_args()

    out_base = Path(args.out_dir)

    # -- Resolve task list --------------------------------------------------
    if args.tasks:
        selected_tasks = args.tasks
        print(f"Using explicit task list: {len(selected_tasks)} tasks")
    else:
        print("Discovering parameterized tasks...")
        all_tasks = list_parameterized_tasks()
        print(f"  Found {len(all_tasks)} parameterized tasks across "
              f"{len(set(get_category(t) for t in all_tasks))} categories")
        selected_tasks = select_tasks(all_tasks, n=args.n_tasks)
        print(f"  Selected {len(selected_tasks)} representative tasks")

    # Print category breakdown
    by_cat: dict[str, list[str]] = defaultdict(list)
    for t in selected_tasks:
        by_cat[get_category(t)].append(t)
    print("\nCategory breakdown:")
    for cat in sorted(by_cat):
        print(f"  {cat:8s}: {len(by_cat[cat]):2d} tasks  {by_cat[cat]}")

    if args.dry_run:
        print(f"\n[dry-run] Would generate {len(selected_tasks)} tasks × {len(args.seeds)} seeds "
              f"= {len(selected_tasks) * len(args.seeds)} instances")
        print(f"[dry-run] Output directory: {out_base}")
        return

    if args.validate_only:
        print(f"\nValidating existing instances in {out_base} ...")
        results = []
        for task_id in selected_tasks:
            for seed in args.seeds:
                instance_dir = out_base / f"{task_id}_seed{seed}"
                if instance_dir.exists():
                    v = validate_instance(task_id, seed, instance_dir)
                    results.append({"task_id": task_id, "seed": seed, **v})
                    status = "OK" if v["ok"] else f"FAIL: {v['errors']}"
                    print(f"  {task_id}_seed{seed}: {status}")
                else:
                    print(f"  {task_id}_seed{seed}: MISSING")
        n_ok = sum(1 for r in results if r.get("ok"))
        print(f"\n{n_ok}/{len(results)} instances valid")
        return

    # -- Generate instances -------------------------------------------------
    out_base.mkdir(parents=True, exist_ok=True)

    total = len(selected_tasks) * len(args.seeds)
    done = 0
    n_ok = 0
    n_fail = 0
    all_results = []

    print(f"\nGenerating {total} instances ({len(selected_tasks)} tasks × {len(args.seeds)} seeds)...")
    for task_id in selected_tasks:
        for seed in args.seeds:
            done += 1
            result = generate_instance(task_id, seed, out_base)
            all_results.append(result)

            if result["ok"]:
                n_ok += 1
                status = "OK"
            else:
                n_fail += 1
                parts = []
                if result.get("error"):
                    parts.append(result["error"])
                if result.get("validation") and not result["validation"]["ok"]:
                    parts.extend(result["validation"]["errors"])
                if result.get("cross_seed") and not result["cross_seed"]["ok"]:
                    parts.append(result["cross_seed"]["error"])
                status = "FAIL: " + "; ".join(parts)

            print(f"  [{done:4d}/{total}] {task_id}_seed{seed}: {status}")

    # -- Summary -----------------------------------------------------------
    print(f"\n{'='*60}")
    print(f"Generated {n_ok}/{total} instances successfully")
    print(f"Output: {out_base}")
    if n_fail > 0:
        print(f"\nFailed instances ({n_fail}):")
        for r in all_results:
            if not r["ok"]:
                print(f"  {r['task_id']}_seed{r['seed']}: {r.get('error', '')}")

    summary = {
        "total": total,
        "n_ok": n_ok,
        "n_fail": n_fail,
        "seeds": args.seeds,
        "tasks": selected_tasks,
        "results": all_results,
    }

    if args.summary_out:
        Path(args.summary_out).write_text(json.dumps(summary, indent=2))
        print(f"\nSummary written to {args.summary_out}")


if __name__ == "__main__":
    main()
