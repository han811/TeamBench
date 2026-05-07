"""smoke_test_real_llm.py — End-to-end smoke test with a real LLM.

Runs ONE small task × ALL THREE new conditions × ONE seed using Claude Haiku 4.5
via OpenRouter (provider-pinned to anthropic — see openai_adapter.py:371-374).

Purpose
-------
Verify that `VariableEnforcementOrchestrator` executes end-to-end with a real
model. Unit tests already cover the static structure; this covers the dynamic:

  * All three conditions complete without crashing.
  * Tool calls are parsed correctly across the conditions' distinct tool sets.
  * `seed_context` actually reaches the LLM (verified by dialogue log inspection).
  * `grade.sh` produces a `score.json` for each condition.
  * Pass/fail signals are distinct from each other (sanity check, not a claim).

Budget
------
3 runs × ~$0.02/run with Haiku 4.5 ≈ $0.10 total. Bounded above by
max_turns_per_phase × 3 phases = 60 LLM turns per run.

Artifacts
---------
All outputs land in `runs/smoke_test/<condition>/`:
  * `run_dir/` — workspace, messages/dialogue.jsonl, logs, submission
  * `score.json` — grader output
  * `result.json` — OrchestratorResult serialised

Exit code
---------
0 if all three conditions produced a score.json (regardless of pass/fail).
1 if any condition crashed or failed to score.

This is *not* a pass/fail experiment; a smoke test verifies the machine runs.
The experimental result claims only come from `scripts/03_run_all.sh`.
"""
from __future__ import annotations

import json
import os
import sys
import shutil
import time
import traceback
from dataclasses import asdict
from pathlib import Path

# Repo-root imports
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from harness.ablation import AblationCondition, run_ablation_condition  # noqa: E402
from harness.adapters import create_adapter  # noqa: E402
from harness.run_all import setup_run, grade_run  # noqa: E402
from harness.orchestrator import OrchestratorResult  # noqa: E402


EXPERIMENT_DIR = Path(__file__).resolve().parent.parent
SMOKE_DIR = EXPERIMENT_DIR / "runs" / "smoke_test"
TASK_NAME = "P1_policy_config"
SEED = 0
MODEL_ID = "openrouter:anthropic/claude-haiku-4.5"
MAX_TURNS = 12          # keep bounded for budget
MAX_REMEDIATION = 1     # 2 loops max

CONDITIONS = [
    AblationCondition.ENFORCED,
    AblationCondition.ENFORCED_SHARED_HISTORY,
    AblationCondition.PROMPT_ONLY,
]


def _orch_result_to_dict(r: OrchestratorResult) -> dict:
    return {
        "task_id": r.task_id,
        "verdict": r.verdict,
        "remediation_loops": r.remediation_loops,
        "total_turns": r.total_turns,
        "phases": [{"phase": p.phase, "turns_count": len(p.turns)} for p in r.phases],
    }


def _inspect_seed_leaked_to_log(run_dir: Path, condition: str) -> bool:
    """Verify seed delivery via `logs/<role>/seed_context.json` files written
    by VariableEnforcementOrchestrator._seed_if_shared() when share_history=True.

    - `enforced`: no seed expected → pass iff no seed files exist.
    - `enforced_shared_history` / `prompt_only`: pass iff at least one
      seed_context.json was written for executor or verifier phases, and its
      content starts with the expected transcript marker.
    """
    seed_files = list((run_dir / "logs").rglob("seed_context.json"))
    if condition == "enforced":
        return len(seed_files) == 0  # no seed expected, and none should exist
    # Shared-history conditions: seed must materialise for executor/verifier
    if not seed_files:
        return False
    marker = "Prior conversation transcript"
    for path in seed_files:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        msgs = data.get("seed_messages") or []
        if msgs and marker in (msgs[0].get("content") or ""):
            return True
    return False


def run_one_condition(
    condition: AblationCondition, adapter, tasks_dir: Path, out_dir: Path,
) -> dict:
    """Run a single condition. Returns a summary dict."""
    summary: dict = {
        "condition": condition.value,
        "model": MODEL_ID,
        "task": TASK_NAME,
        "seed": SEED,
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "error": None,
        "elapsed_sec": 0.0,
    }
    # Each condition gets its own runs subtree: runs/smoke_test/<cond>/<task>/<run_id>/
    runs_root = out_dir
    if runs_root.exists():
        shutil.rmtree(runs_root)
    runs_root.mkdir(parents=True)

    t0 = time.time()
    try:
        # setup_run builds runs_dir/<task>/<run_id>/ and returns (run_id, run_dir, task_dir)
        run_id, run_dir_str, task_dir_str = setup_run(
            task_name=TASK_NAME,
            tasks_dir=str(tasks_dir),
            runs_dir=str(runs_root),
            seed=SEED,
        )
        run_dir = Path(run_dir_str)
        summary["run_id"] = run_id
        summary["run_dir"] = str(run_dir)

        # Execute condition
        orch_result = run_ablation_condition(
            condition=condition,
            task_dir=task_dir_str,
            run_dir=run_dir_str,
            adapter=adapter,
            max_turns=MAX_TURNS,
            max_remediation=MAX_REMEDIATION,
        )
        summary["orchestrator_result"] = _orch_result_to_dict(orch_result)

        # Score
        score = grade_run(
            task_name=TASK_NAME, task_dir=task_dir_str, run_dir=run_dir_str,
        )
        summary["score"] = score
        summary["pass"] = bool(score.get("pass", False))

        # Verify seed actually reached the LLM (for shared-history conditions)
        summary["seed_leaked"] = _inspect_seed_leaked_to_log(
            run_dir, condition.value,
        )

    except Exception as e:  # noqa: BLE001
        summary["error"] = f"{type(e).__name__}: {e}"
        summary["traceback"] = traceback.format_exc()

    summary["elapsed_sec"] = round(time.time() - t0, 2)
    # Persist summary alongside run_dir
    (out_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, default=str), encoding="utf-8",
    )
    return summary


def main() -> int:
    print("=" * 70)
    print("role_enforcement_ablation — real-LLM smoke test")
    print(f"  Task:    {TASK_NAME}")
    print(f"  Model:   {MODEL_ID}")
    print(f"  Seed:    {SEED}")
    print(f"  Cond:    {[c.value for c in CONDITIONS]}")
    print(f"  Output:  {SMOKE_DIR}")
    print("=" * 70)

    SMOKE_DIR.mkdir(parents=True, exist_ok=True)
    tasks_dir = REPO_ROOT / "tasks"

    # Build adapter once, reuse across conditions.
    # Using Haiku 4.5 via OR — provider pinning to anthropic is already
    # automatic (openai_adapter.py:371-374).
    adapter = create_adapter(model=MODEL_ID, temperature=0.2)

    summaries: list[dict] = []
    for cond in CONDITIONS:
        print(f"\n--- RUNNING: {cond.value} ---")
        out_dir = SMOKE_DIR / cond.value
        summary = run_one_condition(cond, adapter, tasks_dir, out_dir)
        summaries.append(summary)
        status = (
            "ERROR" if summary.get("error")
            else ("PASS" if summary.get("pass") else "FAIL")
        )
        elapsed = summary.get("elapsed_sec", 0)
        turns = summary.get("orchestrator_result", {}).get("total_turns", "?")
        seed_ok = summary.get("seed_leaked")
        print(f"    status={status} elapsed={elapsed}s turns={turns} "
              f"seed_reached_LLM={seed_ok}")
        if summary.get("error"):
            print(f"    ERROR: {summary['error']}")

    # Aggregate summary
    agg_path = SMOKE_DIR / "aggregate_summary.json"
    agg_path.write_text(
        json.dumps(summaries, indent=2, default=str), encoding="utf-8",
    )

    print("\n" + "=" * 70)
    print("Summary:")
    for s in summaries:
        cond = s["condition"]
        if s.get("error"):
            print(f"  {cond:30s} ERROR — {s['error']}")
        else:
            passed = s.get("pass", False)
            score = s.get("score", {}).get("secondary", {}).get("partial_score", "?")
            print(f"  {cond:30s} pass={passed} partial={score} "
                  f"seed_reached={s.get('seed_leaked')}")
    print(f"\n  Aggregate saved to: {agg_path}")
    print("=" * 70)

    # Exit code: 0 iff all three conditions produced a score (no exceptions)
    all_scored = all(
        (s.get("score") is not None) and (s.get("error") is None)
        for s in summaries
    )
    return 0 if all_scored else 1


if __name__ == "__main__":
    sys.exit(main())
