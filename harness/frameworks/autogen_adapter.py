"""
AutoGen framework adapter for TeamBench.

Maps TeamBench's Planner/Executor/Verifier roles onto Microsoft AutoGen's
AssistantAgent + GroupChat model.

Install dependency:
    pip install pyautogen   # or: pip install autogen-agentchat

Architecture mapping:
    TeamBench role      AutoGen construct
    ─────────────────   ──────────────────────────────────────────────────
    Planner             AssistantAgent with read + send_message tools only
    Executor            AssistantAgent with run + read + write + send_message
    Verifier            AssistantAgent with run + read + write(submission) only
    Orchestration       GroupChat with a RoundRobinGroupChatManager
    Tool enforcement    Each agent only registers its role-allowed functions
    Dialogue log        GroupChat messages written to dialogue.jsonl

NOTE: This is a REFERENCE implementation.  The AutoGen API changes between
minor versions; the TODO comments call out where you need to adapt to the
exact pyautogen version you are using.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Callable

try:
    # AutoGen >= 0.2 (pyautogen / autogen-agentchat)
    import autogen  # type: ignore[import]
    _AUTOGEN_AVAILABLE = True
except ImportError:
    _AUTOGEN_AVAILABLE = False

from harness.agent_interface import RoleConfig, Tool, ToolResult
from harness.framework_adapter import (
    FrameworkResult,
    TeamBenchFrameworkAdapter,
    load_task_context,
    setup_run_directory,
)


# ---------------------------------------------------------------------------
# Tool bridging: TeamBench Tool -> AutoGen-callable function
# ---------------------------------------------------------------------------

def _make_autogen_function(tool: Tool) -> Callable[..., str]:
    """Wrap a TeamBench Tool so AutoGen can call it as a Python function.

    AutoGen functions receive keyword arguments and must return a string.
    The wrapper serialises the ToolResult as JSON for AutoGen to relay to
    the LLM.
    """
    def _fn(**kwargs) -> str:
        result: ToolResult = tool.execute(**kwargs)
        return json.dumps({
            "stdout":    result.stdout,
            "stderr":    result.stderr,
            "exit_code": result.exit_code,
        })
    _fn.__name__ = tool.name
    _fn.__doc__ = f"TeamBench tool: {tool.name}"
    return _fn


def _register_tools(
    agent,           # autogen.AssistantAgent
    executor_agent,  # autogen.UserProxyAgent that executes functions
    tools: list[Tool],
) -> None:
    """Register TeamBench tools on an AutoGen agent pair.

    AutoGen uses a two-agent pattern: the AssistantAgent decides which
    function to call; a paired UserProxyAgent (or FunctionCallingExecutor)
    actually runs it.

    TODO: Adjust the registration API to match your pyautogen version:
      - autogen >= 0.3: use agent.register_for_llm() / register_for_execution()
      - autogen 0.2.x:  use autogen.register_function()
    """
    for tool in tools:
        fn = _make_autogen_function(tool)
        try:
            # autogen >= 0.3 API
            agent.register_for_llm(
                name=tool.name,
                description=fn.__doc__ or tool.name,
            )(fn)
            executor_agent.register_for_execution(name=tool.name)(fn)
        except AttributeError:
            # Fallback: autogen 0.2.x flat registration
            autogen.register_function(  # type: ignore[attr-defined]
                fn,
                caller=agent,
                executor=executor_agent,
                name=tool.name,
                description=fn.__doc__ or tool.name,
            )


# ---------------------------------------------------------------------------
# Dialogue logging
# ---------------------------------------------------------------------------

def _write_dialogue(messages: list[dict], dialogue_path: str) -> None:
    """Persist GroupChat message history as dialogue.jsonl."""
    os.makedirs(os.path.dirname(dialogue_path), exist_ok=True)
    from datetime import datetime, timezone
    with open(dialogue_path, "w", encoding="utf-8") as f:
        for i, msg in enumerate(messages):
            entry = {
                "ts":      datetime.now(timezone.utc).isoformat(),
                "turn":    i,
                "role":    msg.get("name", msg.get("role", "unknown")),
                "type":    "message",
                "content": msg.get("content", ""),
            }
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------

class AutoGenAdapter(TeamBenchFrameworkAdapter):
    """Run TeamBench tasks using Microsoft AutoGen framework.

    Creates three AssistantAgents (planner, executor, verifier) and coordinates
    them via an AutoGen GroupChat.  Tool enforcement mirrors TeamBench's native
    role separation: each agent only has access to the tools its RoleConfig
    declares.

    Args:
        model:       LLM model name passed to AutoGen's LLM config (e.g. "gpt-4o").
        temperature: Sampling temperature.
        max_turns:   Maximum GroupChat rounds before termination.
        api_key:     Optional API key override.  Falls back to OPENAI_API_KEY env var.
        base_url:    Optional API base URL (for proxies / Azure / vLLM endpoints).
    """

    def __init__(
        self,
        model: str = "gpt-4o",
        temperature: float = 0.2,
        max_turns: int = 30,
        api_key: str | None = None,
        base_url: str | None = None,
        **kwargs,
    ):
        if not _AUTOGEN_AVAILABLE:
            raise ImportError(
                "AutoGen is not installed. Run: pip install pyautogen"
            )
        self.model = model
        self.temperature = temperature
        self.max_turns = max_turns
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.base_url = base_url

    # ------------------------------------------------------------------
    # TeamBenchFrameworkAdapter interface
    # ------------------------------------------------------------------

    def run_team(
        self,
        task_dir: str,
        run_dir: str,
        roles: dict[str, RoleConfig],
    ) -> FrameworkResult:
        """Run a full Planner -> Executor -> Verifier team via AutoGen GroupChat."""
        paths = setup_run_directory(task_dir, run_dir)
        ctx = load_task_context(task_dir)
        dialogue_path = os.path.join(paths["messages"], "dialogue.jsonl")

        try:
            chat_history = self._run_group_chat(ctx, paths, roles)
            _write_dialogue(chat_history, dialogue_path)
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
            metadata={"turns": len(chat_history)},
        )

    def run_single(
        self,
        task_dir: str,
        run_dir: str,
        role_config: RoleConfig,
    ) -> FrameworkResult:
        """Run a single AutoGen AssistantAgent (oracle/restricted condition)."""
        paths = setup_run_directory(task_dir, run_dir)
        ctx = load_task_context(task_dir)
        dialogue_path = os.path.join(paths["messages"], "dialogue.jsonl")

        try:
            chat_history = self._run_single_agent(ctx, paths, role_config)
            _write_dialogue(chat_history, dialogue_path)
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
            metadata={"turns": len(chat_history)},
        )

    # ------------------------------------------------------------------
    # Internal: GroupChat pipeline
    # ------------------------------------------------------------------

    def _llm_config(self) -> dict:
        """Build AutoGen LLM config dict."""
        cfg: dict[str, Any] = {
            "model": self.model,
            "temperature": self.temperature,
        }
        if self.api_key:
            cfg["api_key"] = self.api_key
        if self.base_url:
            cfg["base_url"] = self.base_url
        return {"config_list": [cfg]}

    def _make_executor_proxy(self, name: str) -> Any:
        """Create a UserProxyAgent that executes tool calls without human input.

        TODO: In autogen >= 0.3 the preferred pattern is to use
        autogen.coding.LocalCommandLineCodeExecutor or
        autogen_agentchat.agents.ToolUseAssistantAgent.  Adjust here.
        """
        return autogen.UserProxyAgent(  # type: ignore[attr-defined]
            name=f"{name}_executor",
            human_input_mode="NEVER",
            max_consecutive_auto_reply=self.max_turns,
            code_execution_config=False,  # We use registered functions, not code blocks
            is_termination_msg=lambda m: "DONE" in (m.get("content") or ""),
        )

    def _run_group_chat(
        self,
        ctx,
        paths: dict[str, str],
        roles: dict[str, RoleConfig],
    ) -> list[dict]:
        """Build three agents and run an AutoGen GroupChat."""
        llm_cfg = self._llm_config()

        # --- Create AssistantAgents for each role ---
        agents = {}
        proxies = {}
        for role_name in ("planner", "executor", "verifier"):
            role_cfg = roles.get(role_name)
            if role_cfg is None:
                continue

            # TODO: In autogen >= 0.3, swap AssistantAgent for the appropriate
            # agent class (e.g. autogen_agentchat.agents.AssistantAgent).
            agent = autogen.AssistantAgent(  # type: ignore[attr-defined]
                name=role_name,
                system_message=role_cfg.system_prompt,
                llm_config=llm_cfg,
                is_termination_msg=lambda m: "DONE" in (m.get("content") or ""),
            )
            proxy = self._make_executor_proxy(role_name)
            _register_tools(agent, proxy, role_cfg.tools)
            agents[role_name] = agent
            proxies[role_name] = proxy

        # --- GroupChat with round-robin speaker selection ---
        # TODO: For autogen >= 0.3, replace GroupChat + GroupChatManager with
        # autogen_agentchat.teams.RoundRobinGroupChat or SelectorGroupChat.
        agent_list = list(agents.values())
        group_chat = autogen.GroupChat(  # type: ignore[attr-defined]
            agents=agent_list,
            messages=[],
            max_round=self.max_turns,
            speaker_selection_method="round_robin",
        )
        manager = autogen.GroupChatManager(  # type: ignore[attr-defined]
            groupchat=group_chat,
            llm_config=llm_cfg,
        )

        # --- Initial prompt to kick off the pipeline ---
        task_id = os.path.basename(ctx.task_dir)
        initial_message = (
            f"Task: {task_id}\n\n"
            f"Spec (Planner and Verifier reference):\n{ctx.spec}\n\n"
            f"Brief (Executor reference):\n{ctx.brief}\n\n"
            "Planner: read the spec, decompose the task, and send your plan to the executor.\n"
            "Executor: implement the solution in the workspace.\n"
            "Verifier: check the result against the spec and write attestation.json.\n"
            "Each agent should output DONE when its role is complete."
        )

        # Initiate the group chat from the planner's perspective
        first_agent = agents.get("planner", agent_list[0])
        first_proxy = proxies.get("planner", list(proxies.values())[0])
        first_proxy.initiate_chat(manager, message=initial_message)

        return group_chat.messages

    def _run_single_agent(
        self,
        ctx,
        paths: dict[str, str],
        role_config: RoleConfig,
    ) -> list[dict]:
        """Run a single AutoGen AssistantAgent for oracle/restricted condition."""
        llm_cfg = self._llm_config()

        agent = autogen.AssistantAgent(  # type: ignore[attr-defined]
            name=role_config.role,
            system_message=role_config.system_prompt,
            llm_config=llm_cfg,
            is_termination_msg=lambda m: "DONE" in (m.get("content") or ""),
        )
        proxy = self._make_executor_proxy(role_config.role)
        _register_tools(agent, proxy, role_config.tools)

        task_id = os.path.basename(ctx.task_dir)
        prompt = (
            f"Task: {task_id}\n\n"
            f"Specification:\n{ctx.spec}\n\n"
            "Complete the task. Write attestation.json when done. Output DONE."
        )
        proxy.initiate_chat(agent, message=prompt, max_turns=self.max_turns)

        # Collect conversation history
        # TODO: In autogen >= 0.3, access chat_result.chat_history instead.
        return proxy.chat_messages.get(agent, [])
