"""
CrewAI framework adapter for TeamBench.

Maps TeamBench's Planner/Executor/Verifier roles onto CrewAI's Agent/Task/Crew model.

Install dependency:
    pip install crewai crewai-tools

Architecture mapping:
    TeamBench role      CrewAI construct
    ─────────────────   ──────────────────────────────────────────────────
    Planner             crewai.Agent with role="Planner", read/message tools
    Executor            crewai.Agent with role="Executor", run/read/write tools
    Verifier            crewai.Agent with role="Verifier", run/read tools
    Orchestration       crewai.Crew with sequential process (Plan->Exec->Verify)
    Tool enforcement    crewai.BaseTool subclass wraps each TeamBench Tool
    Dialogue log        Crew task outputs appended to dialogue.jsonl

NOTE: This is a REFERENCE implementation.  CrewAI's API changes frequently;
the TODO comments mark the exact spots that may need adjustment for your
installed version.
"""
from __future__ import annotations

import json
import os
from typing import Any, Type

try:
    import crewai  # type: ignore[import]
    from crewai import Agent, Crew, Process, Task  # type: ignore[import]
    _CREWAI_AVAILABLE = True
except ImportError:
    _CREWAI_AVAILABLE = False

from harness.agent_interface import RoleConfig, Tool, ToolResult
from harness.framework_adapter import (
    FrameworkResult,
    TeamBenchFrameworkAdapter,
    load_task_context,
    setup_run_directory,
)


# ---------------------------------------------------------------------------
# Tool bridging: TeamBench Tool -> CrewAI BaseTool
# ---------------------------------------------------------------------------

def _make_crewai_tool(tool: Tool) -> Any:
    """Wrap a TeamBench Tool as a CrewAI BaseTool.

    CrewAI tools are Pydantic-based classes with a _run() method.  We
    dynamically create a subclass per tool so that CrewAI's type system
    is satisfied.

    TODO: CrewAI >= 0.70 introduced structured tool inputs via Pydantic schemas.
    If you see validation errors, add an args_schema class attribute here.
    """
    if not _CREWAI_AVAILABLE:
        raise ImportError("crewai is not installed. Run: pip install crewai")

    from crewai.tools import BaseTool  # type: ignore[import]

    tool_instance = tool  # capture for closure

    class _WrappedTool(BaseTool):
        name: str = tool.name
        description: str = f"TeamBench tool: {tool.name}"

        def _run(self, **kwargs) -> str:  # type: ignore[override]
            result: ToolResult = tool_instance.execute(**kwargs)
            return json.dumps({
                "stdout":    result.stdout,
                "stderr":    result.stderr,
                "exit_code": result.exit_code,
            })

    # Give the class a unique name so CrewAI's registry doesn't collide
    _WrappedTool.__name__ = f"TB_{tool.name.capitalize()}Tool"
    return _WrappedTool()


def _crewai_tools_for_role(role_config: RoleConfig) -> list[Any]:
    """Convert a RoleConfig's tools to a list of CrewAI BaseTool instances."""
    return [_make_crewai_tool(t) for t in role_config.tools]


# ---------------------------------------------------------------------------
# Dialogue logging
# ---------------------------------------------------------------------------

def _write_dialogue(task_outputs: list[dict], dialogue_path: str) -> None:
    """Write CrewAI task outputs as dialogue.jsonl entries."""
    os.makedirs(os.path.dirname(dialogue_path), exist_ok=True)
    from datetime import datetime, timezone
    with open(dialogue_path, "w", encoding="utf-8") as f:
        for i, entry in enumerate(task_outputs):
            record = {
                "ts":      datetime.now(timezone.utc).isoformat(),
                "turn":    i,
                "role":    entry.get("agent", "unknown"),
                "type":    "task_output",
                "content": entry.get("output", ""),
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------

class CrewAIAdapter(TeamBenchFrameworkAdapter):
    """Run TeamBench tasks using the CrewAI framework.

    Creates three CrewAI Agents (planner, executor, verifier) and runs them
    as a sequential Crew: plan -> execute -> verify.  Tool enforcement mirrors
    TeamBench's role separation via per-agent tool lists.

    Args:
        model:       LLM model identifier in LiteLLM format (e.g. "openai/gpt-4o",
                     "anthropic/claude-opus-4-5", "gemini/gemini-2.0-flash").
        temperature: Sampling temperature.
        max_turns:   Maximum iterations per CrewAI agent (maps to max_iter).
        verbose:     If True, CrewAI prints agent reasoning to stdout.
    """

    def __init__(
        self,
        model: str = "openai/gpt-4o",
        temperature: float = 0.2,
        max_turns: int = 30,
        verbose: bool = False,
        **kwargs,
    ):
        if not _CREWAI_AVAILABLE:
            raise ImportError(
                "CrewAI is not installed. Run: pip install crewai crewai-tools"
            )
        self.model = model
        self.temperature = temperature
        self.max_turns = max_turns
        self.verbose = verbose

    # ------------------------------------------------------------------
    # TeamBenchFrameworkAdapter interface
    # ------------------------------------------------------------------

    def run_team(
        self,
        task_dir: str,
        run_dir: str,
        roles: dict[str, RoleConfig],
    ) -> FrameworkResult:
        """Run a full Planner -> Executor -> Verifier crew sequentially."""
        paths = setup_run_directory(task_dir, run_dir)
        ctx = load_task_context(task_dir)
        dialogue_path = os.path.join(paths["messages"], "dialogue.jsonl")

        try:
            outputs = self._run_crew(ctx, paths, roles)
            _write_dialogue(outputs, dialogue_path)
        except Exception as exc:
            return FrameworkResult(
                workspace_path=paths["workspace"],
                dialogue_path=dialogue_path,
                error=str(exc),
                success=False,
            )

        return FrameworkResult(
            workspace_path=paths["workspace"],
            attestation_path=os.path.join(paths["submission"], "attestation.json"),
            dialogue_path=dialogue_path,
            success=True,
            metadata={"tasks_completed": len(outputs)},
        )

    def run_single(
        self,
        task_dir: str,
        run_dir: str,
        role_config: RoleConfig,
    ) -> FrameworkResult:
        """Run a single CrewAI Agent (oracle/restricted condition)."""
        paths = setup_run_directory(task_dir, run_dir)
        ctx = load_task_context(task_dir)
        dialogue_path = os.path.join(paths["messages"], "dialogue.jsonl")

        try:
            outputs = self._run_single_agent(ctx, paths, role_config)
            _write_dialogue(outputs, dialogue_path)
        except Exception as exc:
            return FrameworkResult(
                workspace_path=paths["workspace"],
                dialogue_path=dialogue_path,
                error=str(exc),
                success=False,
            )

        return FrameworkResult(
            workspace_path=paths["workspace"],
            attestation_path=os.path.join(paths["submission"], "attestation.json"),
            dialogue_path=dialogue_path,
            success=True,
            metadata={"tasks_completed": len(outputs)},
        )

    # ------------------------------------------------------------------
    # Internal: Crew pipeline
    # ------------------------------------------------------------------

    def _make_llm_config(self) -> dict:
        """Build CrewAI LLM config.

        TODO: CrewAI uses LiteLLM under the hood.  Pass the model in
        LiteLLM format: "openai/gpt-4o", "anthropic/claude-opus-4-5",
        "google/gemini-2.0-flash", etc.  See: https://docs.litellm.ai/docs/
        """
        return {
            "model": self.model,
            "temperature": self.temperature,
        }

    def _make_agent(
        self,
        role_config: RoleConfig,
        backstory_suffix: str = "",
    ) -> Any:
        """Create a CrewAI Agent for a TeamBench role.

        The role's system_prompt becomes the agent's backstory, which CrewAI
        prepends to every LLM call.

        TODO: CrewAI >= 0.70 supports structured output via output_json or
        output_pydantic.  Wire that up for the verifier to produce valid JSON.
        """
        tools = _crewai_tools_for_role(role_config)

        # Map TeamBench role names to human-readable CrewAI role labels
        role_labels = {
            "planner":  "Software Planner",
            "executor": "Software Engineer",
            "verifier": "QA Verifier",
        }
        goals = {
            "planner":  "Analyse the task specification and produce a clear, actionable plan.",
            "executor": "Implement the solution as described by the Planner.",
            "verifier": "Verify the implementation against the spec and write attestation.json.",
        }

        role_name = role_config.role
        return Agent(
            role=role_labels.get(role_name, role_name.capitalize()),
            goal=goals.get(role_name, "Complete the assigned task correctly."),
            backstory=role_config.system_prompt + (f"\n{backstory_suffix}" if backstory_suffix else ""),
            tools=tools,
            llm=self.model,  # TODO: pass llm= as a crewai.LLM object for fine-grained control
            max_iter=self.max_turns,
            verbose=self.verbose,
            allow_delegation=False,  # Enforce role separation; no cross-agent delegation
        )

    def _run_crew(
        self,
        ctx,
        paths: dict[str, str],
        roles: dict[str, RoleConfig],
    ) -> list[dict]:
        """Build and run a sequential Crew."""
        task_id = os.path.basename(ctx.task_dir)
        outputs: list[dict] = []

        # --- Build agents ---
        planner_agent  = self._make_agent(roles["planner"])
        executor_agent = self._make_agent(roles["executor"])
        verifier_agent = self._make_agent(roles["verifier"])

        # --- Define CrewAI tasks (distinct from TeamBench tasks) ---
        # Each CrewAI Task has a description and expected output, and is
        # assigned to a specific agent.

        plan_task = Task(
            description=(
                f"Task ID: {task_id}\n\n"
                f"Full specification:\n{ctx.spec}\n\n"
                "Read the specification carefully. Identify all requirements, hidden constraints, "
                "and edge cases. Produce a structured implementation plan for the Executor."
            ),
            expected_output=(
                "A numbered implementation plan with: requirements summary, step-by-step actions, "
                "files to modify, edge cases to handle, and verification criteria."
            ),
            agent=planner_agent,
        )

        exec_task = Task(
            description=(
                f"Task ID: {task_id}\n\n"
                f"Brief (your view of the task):\n{ctx.brief}\n\n"
                "Follow the Planner's output and implement the solution in the workspace. "
                "Modify only the files described in the plan. "
                f"Workspace directory: {paths['workspace']}"
            ),
            expected_output=(
                "All required workspace files modified. "
                "A summary of changes made and any issues encountered."
            ),
            agent=executor_agent,
            context=[plan_task],  # Receives Planner output
        )

        verify_task = Task(
            description=(
                f"Task ID: {task_id}\n\n"
                f"Full specification:\n{ctx.spec}\n\n"
                "Verify the implementation in the workspace against every requirement in the spec. "
                "Run validation scripts if available. "
                f"Workspace directory: {paths['workspace']}\n"
                f"Submission directory (write attestation.json here): {paths['submission']}"
            ),
            expected_output=(
                "attestation.json written to the submission directory with keys: "
                "task_id, verdict ('pass' or 'fail'), checklist (list of requirement checks)."
            ),
            agent=verifier_agent,
            context=[plan_task, exec_task],  # Receives prior outputs
            # TODO: Uncomment to enforce JSON output structure in CrewAI >= 0.70:
            # output_json=AttestationModel,
        )

        # --- Assemble and run the Crew ---
        crew = Crew(
            agents=[planner_agent, executor_agent, verifier_agent],
            tasks=[plan_task, exec_task, verify_task],
            process=Process.sequential,
            verbose=self.verbose,
        )

        # TODO: crew.kickoff() returns a CrewOutput object in recent versions.
        # Access individual task outputs via crew_output.tasks_output.
        crew_output = crew.kickoff()

        # Collect outputs for dialogue logging
        if hasattr(crew_output, "tasks_output"):
            for task_out in crew_output.tasks_output:
                outputs.append({
                    "agent":  getattr(task_out, "agent", "unknown"),
                    "output": getattr(task_out, "raw", str(task_out)),
                })
        else:
            # Older CrewAI: kickoff() returns a string
            outputs.append({"agent": "crew", "output": str(crew_output)})

        return outputs

    def _run_single_agent(
        self,
        ctx,
        paths: dict[str, str],
        role_config: RoleConfig,
    ) -> list[dict]:
        """Run a single CrewAI Agent for oracle/restricted condition."""
        task_id = os.path.basename(ctx.task_dir)
        agent = self._make_agent(role_config)

        solo_task = Task(
            description=(
                f"Task ID: {task_id}\n\n"
                f"Specification:\n{ctx.spec}\n\n"
                "Complete the entire task: plan, implement, and verify. "
                f"Workspace: {paths['workspace']}\n"
                f"Submission (write attestation.json here): {paths['submission']}"
            ),
            expected_output=(
                "Task completed. attestation.json written with verdict and checklist."
            ),
            agent=agent,
        )

        crew = Crew(
            agents=[agent],
            tasks=[solo_task],
            process=Process.sequential,
            verbose=self.verbose,
        )
        crew_output = crew.kickoff()
        raw = str(crew_output)
        return [{"agent": role_config.role, "output": raw}]
