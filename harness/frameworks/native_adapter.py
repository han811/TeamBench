"""
Native TeamBench adapter — wraps the built-in orchestrator.

This adapter uses the same AgentLoop + ToolCallAdapter path that the
harness.run_task module uses.  It is useful as a baseline and as a
reference for what the framework adapters are expected to replicate.

No external framework dependency required.
"""
from __future__ import annotations

import os

from harness.framework_adapter import (
    FrameworkResult,
    TeamBenchFrameworkAdapter,
    setup_run_directory,
)
from harness.agent_interface import RoleConfig


class NativeAdapter(TeamBenchFrameworkAdapter):
    """Run TeamBench tasks using the built-in AgentLoop orchestrator.

    This is the reference 'framework' adapter — it delegates directly to the
    native harness.orchestrator pipeline and exists so the framework CLI
    (scripts/run_with_framework.py) can use --framework native without any
    special-casing.
    """

    def __init__(
        self,
        model: str = "gemini-3-flash-preview",
        temperature: float = 0.2,
        max_turns: int = 30,
        **kwargs,
    ):
        self.model = model
        self.temperature = temperature
        self.max_turns = max_turns

    # ------------------------------------------------------------------
    # TeamBenchFrameworkAdapter interface
    # ------------------------------------------------------------------

    def run_team(
        self,
        task_dir: str,
        run_dir: str,
        roles: dict[str, RoleConfig],
    ) -> FrameworkResult:
        """Run the native Planner -> Executor -> Verifier pipeline."""
        paths = setup_run_directory(task_dir, run_dir)
        try:
            self._run_native_pipeline(task_dir, run_dir)
        except Exception as exc:
            return FrameworkResult(
                workspace_path=paths["workspace"],
                dialogue_path=os.path.join(paths["messages"], "dialogue.jsonl"),
                error=str(exc),
                success=False,
            )
        return FrameworkResult(
            workspace_path=paths["workspace"],
            attestation_path=os.path.join(paths["submission"], "attestation.json"),
            dialogue_path=os.path.join(paths["messages"], "dialogue.jsonl"),
            success=True,
        )

    def run_single(
        self,
        task_dir: str,
        run_dir: str,
        role_config: RoleConfig,
    ) -> FrameworkResult:
        """Run the native single-agent loop (oracle condition)."""
        paths = setup_run_directory(task_dir, run_dir)
        try:
            self._run_native_single(task_dir, run_dir, role_config)
        except Exception as exc:
            return FrameworkResult(
                workspace_path=paths["workspace"],
                dialogue_path=os.path.join(paths["messages"], "dialogue.jsonl"),
                error=str(exc),
                success=False,
            )
        return FrameworkResult(
            workspace_path=paths["workspace"],
            attestation_path=os.path.join(paths["submission"], "attestation.json"),
            dialogue_path=os.path.join(paths["messages"], "dialogue.jsonl"),
            success=True,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _run_native_pipeline(self, task_dir: str, run_dir: str) -> None:
        """Delegate to the native harness.run_task module."""
        from harness.run_task import run_task
        run_task(
            task_dir=task_dir,
            run_dir=run_dir,
            model=self.model,
            temperature=self.temperature,
            max_turns=self.max_turns,
            condition="full",
        )

    def _run_native_single(
        self, task_dir: str, run_dir: str, role_config: RoleConfig
    ) -> None:
        """Run a single agent loop with the given role config."""
        from harness.adapters import create_adapter
        from harness.agent_loop import AgentLoop

        adapter = create_adapter(self.model, temperature=self.temperature)
        messages_dir = os.path.join(run_dir, "messages")
        log_dir = os.path.join(run_dir, "logs", role_config.role)
        loop = AgentLoop(
            role_config=role_config,
            adapter=adapter,
            messages_dir=messages_dir,
            log_dir=log_dir,
            max_turns=self.max_turns,
        )
        task_id = os.path.basename(task_dir)
        loop.run(
            f"Task ID: {task_id}\n"
            "Complete the task described in your system prompt. "
            "When done, write attestation.json and output DONE."
        )
