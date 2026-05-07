"""02_select_tasks.py.

Deterministic stratified selection of 25 tasks for the role-enforcement
ablation, using the persisted TNI classification in
shared/paper/tni_report.json.

Stratification (locked in experiment.yaml):
    HIGH-TNI    : 10
    TEAM-HELPS  :  8
    TEAM-HURTS  :  5
    NEUTRAL     :  2

Determinism:
    Sort within stratum by task_id, then random.Random(42).shuffle, take top N.
    Same input always yields the same output.

Output:
    config/task_selection.json with chosen tasks, stratum breakdown, source
    commit, and the within-stratum seed.
"""
from __future__ import annotations

import json
import random
import subprocess
import sys
from pathlib import Path

EXP_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = EXP_DIR.parent.parent
TNI_REPORT = REPO_ROOT / "shared" / "paper" / "tni_report.json"
OUT = EXP_DIR / "config" / "task_selection.json"

STRATA = [
    ("HIGH-TNI", 10),
    ("TEAM-HELPS", 8),
    ("TEAM-HURTS", 5),
    ("NEUTRAL", 2),
]
SEED = 42


def _git_head() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True,
        ).strip()
    except Exception:
        return "unknown"


def _task_dir_exists(task_id: str) -> bool:
    return (REPO_ROOT / "tasks" / task_id).is_dir()


def main() -> int:
    if not TNI_REPORT.exists():
        print(f"ERROR: {TNI_REPORT} missing", file=sys.stderr)
        return 1

    report = json.loads(TNI_REPORT.read_text())
    tasks = report["tasks"]

    by_class: dict[str, list[str]] = {name: [] for name, _ in STRATA}
    skipped_no_dir: list[str] = []
    for t in tasks:
        cls = t.get("classification")
        tid = t.get("task_id")
        if cls not in by_class or not tid:
            continue
        if not _task_dir_exists(tid):
            skipped_no_dir.append(tid)
            continue
        by_class[cls].append(tid)

    chosen: dict[str, list[str]] = {}
    rng = random.Random(SEED)
    for name, n in STRATA:
        pool = sorted(by_class[name])
        if len(pool) < n:
            print(
                f"ERROR: stratum {name} has {len(pool)} candidates, need {n}",
                file=sys.stderr,
            )
            return 2
        rng.shuffle(pool)
        chosen[name] = pool[:n]

    flat = [tid for ids in chosen.values() for tid in ids]
    payload = {
        "version": 1,
        "selection_seed": SEED,
        "git_commit": _git_head(),
        "source_report": str(TNI_REPORT.relative_to(REPO_ROOT)),
        "stratification": {name: n for name, n in STRATA},
        "stratum_pool_sizes": {name: len(by_class[name]) for name, _ in STRATA},
        "selected_by_stratum": chosen,
        "selected_flat": flat,
        "skipped_missing_task_dir": sorted(skipped_no_dir),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"Wrote {OUT}")
    print(f"Total selected: {len(flat)}")
    for name, ids in chosen.items():
        print(f"  {name:12s} ({len(ids)}): {ids}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
