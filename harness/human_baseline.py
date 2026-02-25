"""
TeamBench human baseline runner.

Usage:
    python -m harness.human_baseline --task P1_policy_config --seed 42
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import shutil
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def ts() -> float:
    """Return current monotonic time in seconds."""
    return time.monotonic()


def elapsed_str(seconds: float) -> str:
    m = int(seconds) // 60
    s = int(seconds) % 60
    return f"{m}m {s:02d}s"


def write_json(path: str, obj: dict) -> None:
    pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)


def read_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def separator(char: str = "=", width: int = 60) -> None:
    print(char * width)


def prompt(msg: str) -> str:
    """Print msg and return stripped user input."""
    try:
        return input(msg).strip()
    except (EOFError, KeyboardInterrupt):
        print("\n\nSession interrupted. Partial results may have been saved.")
        sys.exit(1)


def wait_for_enter(msg: str = "Press Enter to continue...") -> None:
    prompt(msg)


# ---------------------------------------------------------------------------
# Participant ID management
# ---------------------------------------------------------------------------

PARTICIPANT_ID_FILE = pathlib.Path.home() / ".teambench_participant_id"


def get_or_create_participant_id() -> str:
    if PARTICIPANT_ID_FILE.exists():
        pid = PARTICIPANT_ID_FILE.read_text().strip()
        if pid:
            return pid
    pid = "hb_" + uuid.uuid4().hex[:12]
    PARTICIPANT_ID_FILE.write_text(pid)
    print(f"\nNew participant ID created: {pid}")
    print(f"Stored at: {PARTICIPANT_ID_FILE}")
    print("This ID will be reused for all your tasks in this study.\n")
    return pid


# ---------------------------------------------------------------------------
# Workspace setup
# ---------------------------------------------------------------------------

def setup_workspace(task_dir: str, workspace_dir: str, reports_dir: str, run_id: str, seed: int) -> None:
    """Copy task workspace snapshot and run setup.sh if present."""
    seed_src = os.path.join(task_dir, "workspace")
    if os.path.isdir(seed_src):
        for item in os.listdir(seed_src):
            s = os.path.join(seed_src, item)
            d = os.path.join(workspace_dir, item)
            if os.path.isdir(s):
                shutil.copytree(s, d, dirs_exist_ok=True)
            else:
                shutil.copy2(s, d)

    # Try parameterized generator first, fall back to setup.sh
    try:
        from generators.registry import has_generator, get_generator  # type: ignore
        if has_generator(os.path.basename(task_dir)):
            gen = get_generator(os.path.basename(task_dir))
            result = gen.generate(seed=seed)
            gen.write_to_disk(result, workspace_dir=workspace_dir, reports_dir=reports_dir)
            with open(os.path.join(task_dir, "spec.md"), "w") as f:
                f.write(result.spec_md)
            with open(os.path.join(task_dir, "brief.md"), "w") as f:
                f.write(result.brief_md)
            print(f"  Generated parameterized instance (seed={seed})")
            return
    except ImportError:
        pass

    setup = os.path.join(task_dir, "setup.sh")
    if os.path.isfile(setup):
        subprocess.run(
            ["bash", setup, workspace_dir, reports_dir, run_id, str(seed)],
            check=True,
        )


# ---------------------------------------------------------------------------
# Phase runners
# ---------------------------------------------------------------------------

TIME_LIMIT_SEC = 1800  # 30 minutes
WARN_AT_SEC = 1500     # 25 minutes


def run_phase1(task_dir: str, workspace_dir: str, global_start: float) -> float:
    """Planner phase. Returns phase duration in seconds."""
    separator()
    print("PHASE 1 — PLANNER")
    separator()
    print()
    print("Permitted reads:")
    print(f"  tasks/<task_id>/spec.md  ->  {os.path.join(task_dir, 'spec.md')}")
    print()
    print("Required output:")
    print(f"  workspace/plan.md  ->  {os.path.join(workspace_dir, 'plan.md')}")
    print()
    print("Instructions:")
    print("  1. Read spec.md carefully.")
    print("  2. Write plan.md describing your approach, intended changes, and any risks.")
    print("  3. Do NOT look at brief.md or any workspace files yet.")
    print("  4. Return here and press Enter when plan.md is written and saved.")
    print()
    print(f"Suggested time budget: up to 10 minutes.")
    separator("-")

    phase_start = ts()
    wait_for_enter("\n[Phase 1 complete] Press Enter when plan.md is saved... ")
    phase_end = ts()

    duration = phase_end - phase_start

    # Verify plan.md was written
    plan_path = os.path.join(workspace_dir, "plan.md")
    if not os.path.isfile(plan_path):
        print(f"\nWARNING: plan.md not found at {plan_path}")
        print("Please write plan.md before proceeding. Press Enter when ready.")
        wait_for_enter()

    elapsed_total = phase_end - global_start
    print(f"\n  Phase 1 done in {elapsed_str(duration)}  |  Total elapsed: {elapsed_str(elapsed_total)}")
    if elapsed_total >= WARN_AT_SEC:
        print(f"  WARNING: {elapsed_str(elapsed_total)} elapsed — approaching 30-minute limit.")
    print()
    return duration


def run_phase2(task_dir: str, workspace_dir: str, global_start: float) -> float:
    """Executor phase. Returns phase duration in seconds."""
    separator()
    print("PHASE 2 — EXECUTOR")
    separator()
    print()
    print("Permitted reads:")
    print(f"  tasks/<task_id>/brief.md  ->  {os.path.join(task_dir, 'brief.md')}")
    print(f"  workspace/plan.md         ->  {os.path.join(workspace_dir, 'plan.md')}")
    print()
    print("Forbidden during this phase:")
    print("  spec.md  (re-reading it violates role discipline)")
    print()
    print("Required output:")
    print("  Edit workspace files to satisfy the task requirements.")
    print()
    print("Instructions:")
    print("  1. Read brief.md and your plan.md.")
    print("  2. Make all necessary changes to the workspace.")
    print("  3. You may use your IDE, terminal, web search, or offline docs.")
    print("  4. LLM assistance (Copilot, ChatGPT, Claude, etc.) is NOT permitted.")
    print("  5. Return here and press Enter when all changes are saved.")
    print()
    print("Suggested time budget: up to 15 minutes.")
    separator("-")

    phase_start = ts()

    # Warn at 25 minutes total
    elapsed_total_at_start = phase_start - global_start
    remaining_before_warn = WARN_AT_SEC - elapsed_total_at_start
    if remaining_before_warn > 0:
        print(f"\n  (Time remaining before 25-min warning: ~{elapsed_str(remaining_before_warn)})")

    wait_for_enter("\n[Phase 2 complete] Press Enter when workspace edits are saved... ")
    phase_end = ts()

    duration = phase_end - phase_start
    elapsed_total = phase_end - global_start
    print(f"\n  Phase 2 done in {elapsed_str(duration)}  |  Total elapsed: {elapsed_str(elapsed_total)}")
    if elapsed_total >= WARN_AT_SEC:
        print(f"  WARNING: {elapsed_str(elapsed_total)} elapsed — approaching 30-minute limit.")
    print()
    return duration


def run_phase3(task_dir: str, workspace_dir: str, submission_dir: str, global_start: float) -> tuple[float, dict]:
    """
    Verifier phase. Returns (phase_duration_sec, attestation_dict).
    Writes submission/attestation.json.
    """
    separator()
    print("PHASE 3 — VERIFIER")
    separator()
    print()
    print("Permitted reads:")
    print(f"  tasks/<task_id>/spec.md  ->  {os.path.join(task_dir, 'spec.md')}")
    print(f"  workspace/**             ->  {workspace_dir}")
    print()
    print("Forbidden during this phase:")
    print("  Modifying any workspace files.")
    print()
    print("Instructions:")
    print("  1. Re-read spec.md and review the workspace.")
    print("  2. Verify each criterion from spec.md is satisfied.")
    print("  3. Return here and answer the prompts to record your attestation.")
    separator("-")

    phase_start = ts()
    wait_for_enter("\nPress Enter when you are ready to record your attestation... ")

    # Collect verdict
    print()
    while True:
        verdict_raw = prompt("Verdict — did the workspace satisfy the task? [pass/fail]: ").lower()
        if verdict_raw in ("pass", "fail", "p", "f"):
            verdict = "pass" if verdict_raw.startswith("p") else "fail"
            break
        print("  Please enter 'pass' or 'fail'.")

    # Collect checklist items
    print()
    print("Now record your checklist. Enter one criterion at a time.")
    print("Format: brief criterion description, then whether it passed.")
    print("Press Enter with an empty criterion name to finish.\n")

    checklist: list[dict] = []
    idx = 1
    while True:
        criterion = prompt(f"  Criterion {idx} (or blank to finish): ")
        if not criterion:
            break
        ok_raw = prompt(f"    Did it pass? [y/n]: ").lower()
        ok = ok_raw.startswith("y")
        note = prompt(f"    Brief note (optional): ")
        checklist.append({"id": f"c{idx}", "criterion": criterion, "ok": ok, "note": note})
        idx += 1

    if not checklist:
        print("  (No checklist items recorded.)")

    phase_end = ts()
    duration = phase_end - phase_start
    elapsed_total = phase_end - global_start
    overtime = elapsed_total > TIME_LIMIT_SEC

    # Build attestation
    attestation = {
        "task_id": os.path.basename(task_dir),
        "run_id": "",  # filled in by caller
        "verdict": verdict,
        "checklist": checklist,
        "workspace_sha256": "",
        "reports_sha256": "",
    }

    # Write attestation.json to submission dir
    att_path = os.path.join(submission_dir, "attestation.json")
    pathlib.Path(submission_dir).mkdir(parents=True, exist_ok=True)
    write_json(att_path, attestation)

    print(f"\n  Attestation written to: {att_path}")
    print(f"  Phase 3 done in {elapsed_str(duration)}  |  Total elapsed: {elapsed_str(elapsed_total)}")
    if overtime:
        print(f"  NOTE: Total time exceeded the 30-minute limit ({elapsed_str(elapsed_total)}).")
    print()
    return duration, attestation


# ---------------------------------------------------------------------------
# Grading
# ---------------------------------------------------------------------------

def run_grader(task: str, run_dir: str, seed: int) -> dict:
    """Invoke grade_task and return the parsed score dict."""
    separator()
    print("GRADING")
    separator()
    print()
    result = subprocess.run(
        [
            sys.executable, "-m", "harness.grade_task",
            "--task", task,
            "--run_dir", run_dir,
            "--seed", str(seed),
        ],
        text=True,
        capture_output=False,
    )
    print()

    # Try to read score.json written by the grader
    score_path = os.path.join(run_dir, "reports", "score.json")
    if os.path.isfile(score_path):
        return read_json(score_path)
    return {"pass": False, "failure_modes": ["grader_did_not_write_score_json"], "returncode": result.returncode}


# ---------------------------------------------------------------------------
# Self-report survey
# ---------------------------------------------------------------------------

def collect_self_report() -> dict:
    separator()
    print("SELF-REPORT SURVEY")
    separator()
    print()
    print("Please answer a few short questions about your experience.")
    print()

    # Difficulty
    while True:
        raw = prompt("Difficulty (1=trivial, 5=extremely hard): ")
        if raw.isdigit() and 1 <= int(raw) <= 5:
            difficulty = int(raw)
            break
        print("  Please enter a number from 1 to 5.")

    # Confidence
    while True:
        raw = prompt("Confidence that you passed (1=very unsure, 5=certain): ")
        if raw.isdigit() and 1 <= int(raw) <= 5:
            confidence = int(raw)
            break
        print("  Please enter a number from 1 to 5.")

    # Notes
    print("Optional notes (max 500 chars, press Enter to skip):")
    notes = prompt("> ")[:500]

    return {"difficulty": difficulty, "confidence": confidence, "notes": notes}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description="TeamBench human baseline runner")
    ap.add_argument("--task", required=True, help="Task folder name, e.g. P1_policy_config")
    ap.add_argument("--seed", type=int, default=0, help="Random seed for parameterized task instance")
    ap.add_argument(
        "--baselines_dir",
        default="shared/human_baselines",
        help="Root directory for human baseline results",
    )
    args = ap.parse_args()

    task_id = args.task
    seed = args.seed

    # Resolve paths
    repo_root = pathlib.Path(__file__).parent.parent.resolve()
    task_dir = str(repo_root / "tasks" / task_id)
    if not os.path.isdir(task_dir):
        print(f"ERROR: Task directory not found: {task_dir}", file=sys.stderr)
        sys.exit(1)

    participant_id = get_or_create_participant_id()
    run_id = f"{now_utc()}_{uuid.uuid4().hex[:8]}"

    baselines_root = repo_root / args.baselines_dir
    run_dir = str(baselines_root / participant_id / f"{task_id}_{seed}_{run_id[:15]}")
    workspace_dir = os.path.join(run_dir, "workspace")
    reports_dir = os.path.join(run_dir, "reports")
    submission_dir = os.path.join(run_dir, "submission")

    for d in [workspace_dir, reports_dir, submission_dir]:
        os.makedirs(d, exist_ok=True)

    # Banner
    separator()
    print("TeamBench — Human Baseline Session")
    separator()
    print(f"  Participant : {participant_id}")
    print(f"  Task        : {task_id}")
    print(f"  Seed        : {seed}")
    print(f"  Run ID      : {run_id}")
    print(f"  Run dir     : {run_dir}")
    print(f"  Time limit  : 30 minutes")
    separator()
    print()
    print("IMPORTANT REMINDERS:")
    print("  - Do NOT use any LLM assistant (ChatGPT, Copilot, Claude, etc.)")
    print("  - Follow role constraints for each phase")
    print("  - This is an honor-system study; violations reduce data quality")
    print()
    wait_for_enter("Press Enter to set up the workspace and begin Phase 1... ")
    print()

    # Setup workspace
    print("Setting up workspace...")
    try:
        setup_workspace(task_dir, workspace_dir, reports_dir, run_id, seed)
    except Exception as exc:
        print(f"WARNING: workspace setup encountered an error: {exc}")
        print("Continuing — some tasks do not require setup.")
    print(f"  Workspace ready: {workspace_dir}")
    print()

    global_start = ts()
    session_start_utc = datetime.now(timezone.utc).isoformat()

    # Phase 1: Planner
    phase1_sec = run_phase1(task_dir, workspace_dir, global_start)

    # Phase 2: Executor
    phase2_sec = run_phase2(task_dir, workspace_dir, global_start)

    # Phase 3: Verifier
    phase3_sec, attestation = run_phase3(task_dir, workspace_dir, submission_dir, global_start)
    attestation["run_id"] = run_id
    # Re-write with run_id filled in
    write_json(os.path.join(submission_dir, "attestation.json"), attestation)

    total_sec = ts() - global_start
    overtime = total_sec > TIME_LIMIT_SEC

    # Grade
    score = run_grader(task_id, run_dir, seed)

    # Self-report
    self_report = collect_self_report()

    # Assemble result record
    result = {
        "participant_id": participant_id,
        "task_id": task_id,
        "seed": seed,
        "run_id": run_id,
        "session_start_utc": session_start_utc,
        "phase1_duration_sec": round(phase1_sec, 1),
        "phase2_duration_sec": round(phase2_sec, 1),
        "phase3_duration_sec": round(phase3_sec, 1),
        "total_duration_sec": round(total_sec, 1),
        "overtime": overtime,
        "grader_score": score,
        "passed": bool(score.get("pass", False)),
        "difficulty": self_report["difficulty"],
        "confidence": self_report["confidence"],
        "notes": self_report["notes"],
    }

    # Write final result JSON alongside run dir (flat, easy to collect)
    result_path = str(baselines_root / participant_id / f"{task_id}_{seed}.json")
    write_json(result_path, result)

    # Final summary
    separator()
    print("SESSION COMPLETE")
    separator()
    print(f"  Task        : {task_id}  (seed={seed})")
    print(f"  Total time  : {elapsed_str(total_sec)}" + ("  [OVERTIME]" if overtime else ""))
    print(f"  Result      : {'PASS' if result['passed'] else 'FAIL'}")
    print(f"  Difficulty  : {self_report['difficulty']}/5")
    print(f"  Confidence  : {self_report['confidence']}/5")
    print()
    print(f"  Results saved to: {result_path}")
    print(f"  Full run dir    : {run_dir}")
    separator()
    print()
    print("Thank you for participating in the TeamBench human baseline study.")
    print("Please send the following directory to the study coordinator:")
    print(f"  {baselines_root / participant_id}")
    print()


if __name__ == "__main__":
    main()
