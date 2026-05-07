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
# Interaction logging
# ---------------------------------------------------------------------------

class InteractionLogger:
    """Captures timestamped phase events and activity metrics for later analysis.

    Mirrors the objective communication measures from O'Bryan et al. (2022)
    adapted to a role-separated coding task:
      - phase durations (analog of speaking time)
      - activity counts per role (analog of turn count)
      - idle gaps between phases (analog of silence gap duration)
    """

    def __init__(self) -> None:
        self.events: list[dict] = []
        self._phase_start: float | None = None

    def phase_start(self, phase: str, role: str) -> None:
        self._phase_start = ts()
        self.events.append({
            "type": "phase_start",
            "phase": phase,
            "role": role,
            "wall_time": datetime.now(timezone.utc).isoformat(),
            "monotonic": self._phase_start,
        })

    def phase_end(self, phase: str, role: str, artifacts: list[str] | None = None) -> None:
        now = ts()
        duration = now - self._phase_start if self._phase_start else 0.0
        self.events.append({
            "type": "phase_end",
            "phase": phase,
            "role": role,
            "wall_time": datetime.now(timezone.utc).isoformat(),
            "monotonic": now,
            "duration_sec": round(duration, 1),
            "artifacts_produced": artifacts or [],
        })
        self._phase_start = None

    def compute_metrics(self) -> dict:
        """Derive objective interaction metrics from the event log."""
        phases = {}
        for ev in self.events:
            if ev["type"] == "phase_end":
                phases[ev["phase"]] = {
                    "role": ev["role"],
                    "duration_sec": ev["duration_sec"],
                    "artifacts": ev["artifacts_produced"],
                }

        durations = [p["duration_sec"] for p in phases.values()]
        total = sum(durations) if durations else 1.0

        # Participation balance: 1 - Gini coefficient of phase durations
        # Perfect balance = 1.0, one phase dominates = close to 0
        n = len(durations)
        if n > 1 and total > 0:
            sorted_d = sorted(durations)
            gini_num = sum((2 * (i + 1) - n - 1) * sorted_d[i] for i in range(n))
            gini = gini_num / (n * sum(sorted_d)) if sum(sorted_d) > 0 else 0
            participation_balance = round(1.0 - gini, 3)
        else:
            participation_balance = 1.0

        # Phase time ratios (analog of speaking time ratio)
        time_ratios = {}
        for phase_name, pdata in phases.items():
            time_ratios[phase_name] = round(pdata["duration_sec"] / total, 3) if total > 0 else 0

        # Idle gaps between consecutive phases
        phase_ends = [ev for ev in self.events if ev["type"] == "phase_end"]
        phase_starts = [ev for ev in self.events if ev["type"] == "phase_start"]
        idle_gaps = []
        for i in range(1, len(phase_starts)):
            if i - 1 < len(phase_ends):
                gap = phase_starts[i]["monotonic"] - phase_ends[i - 1]["monotonic"]
                idle_gaps.append(round(gap, 1))

        return {
            "phase_count": len(phases),
            "total_duration_sec": round(total, 1),
            "phase_durations": {k: v["duration_sec"] for k, v in phases.items()},
            "phase_time_ratios": time_ratios,
            "participation_balance": participation_balance,
            "idle_gaps_sec": idle_gaps,
            "mean_idle_gap_sec": round(sum(idle_gaps) / len(idle_gaps), 1) if idle_gaps else 0.0,
        }

    def to_dict(self) -> dict:
        return {
            "events": self.events,
            "metrics": self.compute_metrics(),
        }


# ---------------------------------------------------------------------------
# CATME-lite teamwork survey (distilled from CATME BARS v5)
# ---------------------------------------------------------------------------
# Reference: Ohland et al. (2012). "The comprehensive assessment of team
# member effectiveness." Academy of Management Learning & Education, 11(4).
#
# Five dimensions, each rated 1-5 Likert:
#   1. Contributing to the Team's Work
#   2. Interacting with Teammates
#   3. Keeping the Team on Track
#   4. Expecting Quality
#   5. Having Relevant Knowledge, Skills, and Abilities

CATME_DIMENSIONS = [
    {
        "id": "contributing",
        "label": "Contributing to the Team's Work",
        "prompt": "This role contributed meaningfully to the task",
        "anchors": {
            1: "Did not do a fair share; delivered sloppy or incomplete work",
            3: "Completed assignments on time with acceptable quality",
            5: "Made important contributions; helped teammates having difficulty",
        },
    },
    {
        "id": "interacting",
        "label": "Interacting with Teammates",
        "prompt": "This role communicated effectively with the team",
        "anchors": {
            1: "Took actions without input; did not share information",
            3: "Listened and shared information; participated in activities",
            5: "Encouraged communication; asked for and used feedback",
        },
    },
    {
        "id": "keeping_on_track",
        "label": "Keeping the Team on Track",
        "prompt": "This role helped keep the team focused and on track",
        "anchors": {
            1: "Unaware of progress; avoided discussing problems",
            3: "Noticed changes; alerted team when success was threatened",
            5: "Monitored progress; gave specific, timely, constructive feedback",
        },
    },
    {
        "id": "expecting_quality",
        "label": "Expecting Quality",
        "prompt": "This role maintained high quality standards",
        "anchors": {
            1: "Satisfied even if the work did not meet standards",
            3: "Encouraged good work; wanted the team to meet requirements",
            5: "Motivated the team to do excellent work; believed in high standards",
        },
    },
    {
        "id": "knowledge_skills",
        "label": "Having Relevant Knowledge, Skills, and Abilities",
        "prompt": "This role demonstrated relevant technical skills",
        "anchors": {
            1: "Missing basic qualifications; unable to contribute",
            3: "Acquired knowledge needed; could perform some tasks of other members",
            5: "Demonstrated strong skills; could perform the role of any team member",
        },
    },
]

ROLES_TEAM = ["Planner", "Executor", "Verifier"]


def _collect_likert(dimension: dict, target_label: str) -> int:
    """Prompt for a single 1-5 Likert rating."""
    print(f"\n  {dimension['prompt']}")
    print(f"    1 = {dimension['anchors'][1]}")
    print(f"    3 = {dimension['anchors'][3]}")
    print(f"    5 = {dimension['anchors'][5]}")
    while True:
        raw = prompt(f"  Rate {target_label} (1-5): ")
        if raw.isdigit() and 1 <= int(raw) <= 5:
            return int(raw)
        print("    Please enter a number from 1 to 5.")


def collect_catme_survey(mode: str, own_role: str | None = None) -> dict:
    """Collect CATME-lite peer and self ratings.

    For team mode: rate each other role + self on all 5 dimensions.
    For solo mode: self-rate only.

    Returns dict with 'peer_ratings', 'self_rating', and 'open_ended'.
    """
    separator()
    print("TEAMWORK EFFECTIVENESS SURVEY  (CATME-lite)")
    separator()
    print()
    print("Based on the CATME Behaviorally Anchored Rating Scale (Ohland et al., 2012).")
    print("Please rate each role on five dimensions of team effectiveness.")
    print("This takes approximately 3 minutes.")
    print()

    ratings: dict[str, dict[str, int]] = {}

    if mode == "team" and own_role:
        # Determine which roles to rate as peers
        other_roles = [r for r in ROLES_TEAM if r != own_role]

        # Peer ratings
        for role in other_roles:
            print(f"\n{'─' * 50}")
            print(f"  Rating: {role}")
            print(f"{'─' * 50}")
            role_ratings = {}
            for dim in CATME_DIMENSIONS:
                role_ratings[dim["id"]] = _collect_likert(dim, role)
            ratings[role.lower()] = role_ratings

        # Self rating
        print(f"\n{'─' * 50}")
        print(f"  Self-Rating: {own_role} (yourself)")
        print(f"{'─' * 50}")
        self_ratings = {}
        for dim in CATME_DIMENSIONS:
            self_ratings[dim["id"]] = _collect_likert(dim, "yourself")
        ratings["self"] = self_ratings
    else:
        # Solo mode: self-rate only
        print("\n  Solo mode — self-assessment only.")
        self_ratings = {}
        for dim in CATME_DIMENSIONS:
            self_ratings[dim["id"]] = _collect_likert(dim, "yourself")
        ratings["self"] = self_ratings

    # Open-ended question
    print(f"\n{'─' * 50}")
    print("What was the most challenging part of collaborating on this task?")
    print("(max 500 chars, press Enter to skip)")
    collaboration_challenge = prompt("> ")[:500]

    return {
        "mode": mode,
        "own_role": own_role,
        "peer_ratings": {k: v for k, v in ratings.items() if k != "self"},
        "self_rating": ratings.get("self", {}),
        "open_ended": {
            "collaboration_challenge": collaboration_challenge,
        },
    }


# ---------------------------------------------------------------------------
# Self-report survey (task-level, kept alongside CATME)
# ---------------------------------------------------------------------------

def collect_self_report() -> dict:
    separator()
    print("TASK SELF-REPORT")
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
    ilog = InteractionLogger()

    # Phase 1: Planner
    ilog.phase_start("phase1_planner", "planner")
    phase1_sec = run_phase1(task_dir, workspace_dir, global_start)
    ilog.phase_end("phase1_planner", "planner", artifacts=["plan.md"])

    # Phase 2: Executor
    ilog.phase_start("phase2_executor", "executor")
    phase2_sec = run_phase2(task_dir, workspace_dir, global_start)
    ilog.phase_end("phase2_executor", "executor", artifacts=["workspace_edits"])

    # Phase 3: Verifier
    ilog.phase_start("phase3_verifier", "verifier")
    phase3_sec, attestation = run_phase3(task_dir, workspace_dir, submission_dir, global_start)
    ilog.phase_end("phase3_verifier", "verifier", artifacts=["attestation.json"])
    attestation["run_id"] = run_id
    # Re-write with run_id filled in
    write_json(os.path.join(submission_dir, "attestation.json"), attestation)

    total_sec = ts() - global_start
    overtime = total_sec > TIME_LIMIT_SEC

    # Grade
    score = run_grader(task_id, run_dir, seed)

    # Determine mode (solo vs team) — currently CLI is single-person sequential
    # but we collect the survey to characterize perceived role effectiveness
    mode = "solo"  # TODO: set to "team" when multi-player web UI is used
    own_role = None

    # CATME-lite teamwork survey (collected immediately per Daniel's guidance)
    catme = collect_catme_survey(mode=mode, own_role=own_role)

    # Task-level self-report (kept for backward compatibility)
    self_report = collect_self_report()

    # Write interaction log
    interaction_data = ilog.to_dict()
    ilog_path = os.path.join(run_dir, "interaction_log.json")
    write_json(ilog_path, interaction_data)

    # Write CATME survey
    catme_path = os.path.join(run_dir, "catme_survey.json")
    write_json(catme_path, catme)

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
        "catme_survey": catme,
        "interaction_metrics": interaction_data["metrics"],
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
    metrics = interaction_data["metrics"]
    print(f"  Part. balance : {metrics['participation_balance']}")
    print()
    print(f"  Results saved to     : {result_path}")
    print(f"  Interaction log      : {ilog_path}")
    print(f"  CATME survey         : {catme_path}")
    print(f"  Full run dir         : {run_dir}")
    separator()
    print()
    print("Thank you for participating in the TeamBench human baseline study.")
    print("Please send the following directory to the study coordinator:")
    print(f"  {baselines_root / participant_id}")
    print()


if __name__ == "__main__":
    main()
