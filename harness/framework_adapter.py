"""
TeamBench Framework Adapter Interface.

External multi-agent frameworks (AutoGen, CrewAI, LangGraph, etc.) implement
TeamBenchFrameworkAdapter to plug into the benchmark evaluation loop.

The interface mirrors the native TeamBench orchestration model:
  - run_team(): full Planner + Executor + Verifier pipeline
  - run_single(): single-agent oracle/restricted condition

Usage:
    from harness.framework_adapter import TeamBenchFrameworkAdapter, load_task_context
    from harness.frameworks import create_framework_adapter

    adapter = create_framework_adapter("autogen", model="gpt-4o")
    roles = build_roles_for_task(task_dir, run_dir)
    result = adapter.run_team(task_dir, run_dir, roles)
    score = grade_framework_result(result, task_name, task_dir)
"""
from __future__ import annotations

import json
import os
import shutil
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

from harness.agent_interface import RoleConfig


# ---------------------------------------------------------------------------
# Result type returned by all framework adapters
# ---------------------------------------------------------------------------

@dataclass
class FrameworkResult:
    """Standardised result from any framework adapter run.

    Attributes:
        workspace_path:   Absolute path to the (possibly modified) workspace directory.
        attestation_path: Absolute path to attestation.json written by the verifier role.
        dialogue_path:    Absolute path to dialogue.jsonl capturing inter-agent messages.
        success:          True if the framework considers the run to have completed without
                          infrastructure errors (does NOT mean the task was solved).
        error:            Non-empty if the framework raised an error during execution.
        metadata:         Framework-specific extra info (token counts, turn counts, etc.).
    """
    workspace_path: str = ""
    attestation_path: str = ""
    dialogue_path: str = ""
    success: bool = False
    error: str = ""
    metadata: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Abstract base class
# ---------------------------------------------------------------------------

class TeamBenchFrameworkAdapter(ABC):
    """Interface for external multi-agent frameworks to run TeamBench tasks.

    Implementing this class lets any framework participate in the benchmark
    without touching the harness internals.  The framework is responsible for:
      1. Interpreting the task files in task_dir.
      2. Orchestrating its agents using the system prompts and tool constraints
         from the provided RoleConfig objects.
      3. Writing the standard output artefacts to run_dir:
           run_dir/workspace/   — modified workspace files
           run_dir/submission/attestation.json
           run_dir/messages/dialogue.jsonl
      4. Returning a FrameworkResult pointing at those artefacts.
    """

    @abstractmethod
    def run_team(
        self,
        task_dir: str,
        run_dir: str,
        roles: dict[str, RoleConfig],
    ) -> FrameworkResult:
        """Run a full team (Planner + Executor + Verifier) on a task.

        Args:
            task_dir: Path to the task directory.  Contains at minimum:
                        spec.md      — full task specification (Planner/Verifier see this)
                        brief.md     — redacted brief (Executor sees this)
                        workspace/   — starting code files
                        grade.sh     — grading script
            run_dir:  Path where outputs should be written.  The adapter should
                      create the following sub-directories if they do not exist:
                        workspace/   — a copy of task_dir/workspace/ for modification
                        submission/  — for attestation.json
                        messages/    — for dialogue.jsonl
                        reports/     — for score.json (written by grade.sh)
            roles:    Dict mapping role names ("planner", "executor", "verifier")
                      to RoleConfig objects.  Each RoleConfig carries:
                        role          — str role name
                        system_prompt — the role's instruction text
                        tools         — list of Tool objects with enforcement already baked in

        Returns:
            FrameworkResult with paths to workspace, attestation, and dialogue.
        """
        raise NotImplementedError

    @abstractmethod
    def run_single(
        self,
        task_dir: str,
        run_dir: str,
        role_config: RoleConfig,
    ) -> FrameworkResult:
        """Run a single agent (oracle or restricted condition).

        Used for the oracle ablation condition where one agent sees both the
        full spec and has full tool access, or for the restricted condition
        where the planner role is dropped.

        Args:
            task_dir:    Path to task directory.
            run_dir:     Path where outputs should be written.
            role_config: RoleConfig for the single agent to run.

        Returns:
            FrameworkResult with paths to workspace, attestation, and dialogue.
        """
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Helper: task context loading
# ---------------------------------------------------------------------------

@dataclass
class TaskContext:
    """Parsed contents of a task directory."""
    task_dir: str
    spec: str          # Contents of spec.md (full specification)
    brief: str         # Contents of brief.md (redacted executor brief)
    workspace_files: dict[str, str]   # filename -> contents for text files
    workspace_path: str               # Absolute path to workspace/ directory
    has_analysis_guidance: bool = False
    analysis_guidance: str = ""


def load_task_context(task_dir: str) -> TaskContext:
    """Read task directory files into a TaskContext.

    Only text files in workspace/ are loaded into workspace_files; binary files
    are skipped but remain available on disk at workspace_path.
    """
    task_dir = os.path.abspath(task_dir)

    def _read(name: str) -> str:
        p = os.path.join(task_dir, name)
        if os.path.isfile(p):
            try:
                with open(p, encoding="utf-8") as f:
                    return f.read()
            except Exception:
                return ""
        return ""

    workspace_dir = os.path.join(task_dir, "workspace")
    workspace_files: dict[str, str] = {}
    if os.path.isdir(workspace_dir):
        for dirpath, _, filenames in os.walk(workspace_dir):
            for fname in filenames:
                fpath = os.path.join(dirpath, fname)
                rel = os.path.relpath(fpath, workspace_dir)
                try:
                    with open(fpath, encoding="utf-8") as f:
                        workspace_files[rel] = f.read()
                except (UnicodeDecodeError, PermissionError):
                    # Skip binary or unreadable files
                    pass

    analysis_guidance = _read("analysis_guidance.md")
    return TaskContext(
        task_dir=task_dir,
        spec=_read("spec.md"),
        brief=_read("brief.md"),
        workspace_files=workspace_files,
        workspace_path=workspace_dir,
        has_analysis_guidance=bool(analysis_guidance),
        analysis_guidance=analysis_guidance,
    )


# ---------------------------------------------------------------------------
# Helper: run directory setup
# ---------------------------------------------------------------------------

def setup_run_directory(task_dir: str, run_dir: str) -> dict[str, str]:
    """Create standard sub-directories inside run_dir and copy workspace.

    Returns a dict of absolute paths:
        workspace  — copied workspace (writable)
        submission — for attestation.json
        messages   — for dialogue.jsonl
        reports    — for score.json
    """
    run_dir = os.path.abspath(run_dir)
    paths = {
        "workspace":  os.path.join(run_dir, "workspace"),
        "submission": os.path.join(run_dir, "submission"),
        "messages":   os.path.join(run_dir, "messages"),
        "reports":    os.path.join(run_dir, "reports"),
    }
    for p in paths.values():
        os.makedirs(p, exist_ok=True)

    # Copy task workspace into run_dir/workspace/ if it hasn't been done yet
    src_workspace = os.path.join(os.path.abspath(task_dir), "workspace")
    dst_workspace = paths["workspace"]
    if os.path.isdir(src_workspace) and not os.listdir(dst_workspace):
        shutil.copytree(src_workspace, dst_workspace, dirs_exist_ok=True)

    return paths


# ---------------------------------------------------------------------------
# Helper: grading
# ---------------------------------------------------------------------------

def grade_framework_result(
    result: FrameworkResult,
    task_name: str,
    task_dir: str,
) -> dict:
    """Grade a completed FrameworkResult using the task's grade.sh.

    This is a thin wrapper around harness.run_all.grade_run that accepts a
    FrameworkResult and resolves run_dir from result.workspace_path.

    Args:
        result:    The FrameworkResult returned by the adapter.
        task_name: The task identifier string (e.g. "MULTI1_fullstack_fix").
        task_dir:  Path to the task directory containing grade.sh.

    Returns:
        Score dict with keys: pass, primary, secondary, failure_modes.
    """
    if not result.success:
        return {
            "pass": False,
            "primary": {"success": 0},
            "secondary": {},
            "failure_modes": ["framework_error", result.error or "unknown"],
        }

    # Infer run_dir as the parent of workspace/
    run_dir = os.path.dirname(os.path.abspath(result.workspace_path))

    from harness.run_all import grade_run
    return grade_run(task_name, task_dir, run_dir)


# ---------------------------------------------------------------------------
# Helper: build standard RoleConfigs for a task
# ---------------------------------------------------------------------------

def build_team_roles(
    task_dir: str,
    run_dir: str,
) -> dict[str, RoleConfig]:
    """Build the standard Planner/Executor/Verifier RoleConfigs for a task.

    This uses the same factory functions as the native harness so framework
    adapters get identical system prompts and tool enforcement.

    Args:
        task_dir: Path to the task directory.
        run_dir:  Path to the run output directory (must already be set up via
                  setup_run_directory()).

    Returns:
        Dict with keys "planner", "executor", "verifier" mapping to RoleConfig.
    """
    from harness.agent_interface import (
        make_planner_config,
        make_executor_config,
        make_verifier_config,
    )

    task_dir = os.path.abspath(task_dir)
    run_dir = os.path.abspath(run_dir)

    spec_path   = os.path.join(task_dir, "spec.md")
    brief_path  = os.path.join(task_dir, "brief.md")
    workspace   = os.path.join(run_dir, "workspace")
    reports     = os.path.join(run_dir, "reports")
    messages    = os.path.join(run_dir, "messages")
    submission  = os.path.join(run_dir, "submission")

    return {
        "planner":  make_planner_config(spec_path, messages, task_dir),
        "executor": make_executor_config(
            brief_path, workspace, reports, messages, submission, task_dir
        ),
        "verifier": make_verifier_config(
            spec_path, workspace, reports, messages, submission, task_dir
        ),
    }
