"""
LangGraph framework adapter for TeamBench.

Maps TeamBench's Planner/Executor/Verifier roles onto a LangGraph StateGraph
with conditional edges for the verification-remediation loop.

Install dependencies:
    pip install langgraph langchain langchain-openai langchain-google-genai

Architecture mapping:
    TeamBench role      LangGraph construct
    ─────────────────   ──────────────────────────────────────────────────
    Planner             Graph node running a ToolNode-augmented LLM chain
    Executor            Graph node running a ToolNode-augmented LLM chain
    Verifier            Graph node running a ToolNode-augmented LLM chain
    Verification loop   Conditional edge: verifier -> executor (fail) | END (pass)
    Tool enforcement    Each node receives only its role-specific StructuredTool list
    State               TypedDict carrying messages, workspace_path, attestation
    Dialogue log        All LangGraph messages written to dialogue.jsonl

NOTE: This is a REFERENCE implementation.  LangGraph's API changes between
patch releases; the TODO comments mark the spots most likely to need
adjustment for your installed version.
"""
from __future__ import annotations

import json
import os
from typing import Any, Literal, Sequence, TypedDict

try:
    # LangGraph >= 0.1
    from langgraph.graph import END, StateGraph  # type: ignore[import]
    from langgraph.prebuilt import ToolNode      # type: ignore[import]
    _LANGGRAPH_AVAILABLE = True
except ImportError:
    _LANGGRAPH_AVAILABLE = False

try:
    from langchain_core.messages import (  # type: ignore[import]
        AIMessage,
        BaseMessage,
        HumanMessage,
        SystemMessage,
        ToolMessage,
    )
    from langchain_core.tools import StructuredTool  # type: ignore[import]
    _LANGCHAIN_AVAILABLE = True
except ImportError:
    _LANGCHAIN_AVAILABLE = False

from harness.agent_interface import RoleConfig, Tool, ToolResult
from harness.framework_adapter import (
    FrameworkResult,
    TeamBenchFrameworkAdapter,
    load_task_context,
    setup_run_directory,
)


# ---------------------------------------------------------------------------
# LangGraph state schema
# ---------------------------------------------------------------------------

class TeamBenchState(TypedDict):
    """State carried through the LangGraph pipeline.

    Attributes:
        messages:       Full conversation history as LangChain BaseMessage objects.
        workspace_path: Absolute path to the writable workspace directory.
        submission_path: Absolute path to the submission directory.
        attestation:    Parsed attestation dict once the verifier writes it.
        verdict:        "pass" | "fail" | "pending" — drives the conditional edge.
        remediation_count: Number of executor remediation loops completed.
    """
    messages: list  # list[BaseMessage] — typed loosely for TypedDict compatibility
    workspace_path: str
    submission_path: str
    attestation: dict
    verdict: str
    remediation_count: int


# ---------------------------------------------------------------------------
# Tool bridging: TeamBench Tool -> LangChain StructuredTool
# ---------------------------------------------------------------------------

def _make_langchain_tool(tool: Tool) -> Any:
    """Wrap a TeamBench Tool as a LangChain StructuredTool.

    StructuredTool accepts keyword arguments and returns a string, which
    is then formatted as a ToolMessage by LangGraph's ToolNode.

    TODO: For tools with complex argument schemas, add an args_schema=
    Pydantic model to improve LLM function-calling reliability.
    """
    if not _LANGCHAIN_AVAILABLE:
        raise ImportError(
            "langchain-core is not installed. Run: pip install langchain"
        )

    tool_instance = tool

    def _fn(**kwargs) -> str:
        result: ToolResult = tool_instance.execute(**kwargs)
        return json.dumps({
            "stdout":    result.stdout,
            "stderr":    result.stderr,
            "exit_code": result.exit_code,
        })

    return StructuredTool.from_function(
        func=_fn,
        name=tool.name,
        description=f"TeamBench tool: {tool.name}",
        return_direct=False,
    )


def _langchain_tools_for_role(role_config: RoleConfig) -> list[Any]:
    """Convert RoleConfig tools to LangChain StructuredTool list."""
    return [_make_langchain_tool(t) for t in role_config.tools]


# ---------------------------------------------------------------------------
# LLM factory
# ---------------------------------------------------------------------------

def _make_llm(model: str, temperature: float, tools: list[Any]) -> Any:
    """Instantiate the correct LangChain LLM and bind tools to it.

    TODO: Add branches here for other providers as needed:
      - Anthropic: from langchain_anthropic import ChatAnthropic
      - Gemini:    from langchain_google_genai import ChatGoogleGenerativeAI
      - Azure:     from langchain_openai import AzureChatOpenAI
      - vLLM:      from langchain_openai import ChatOpenAI with base_url=
    """
    if not _LANGCHAIN_AVAILABLE:
        raise ImportError("langchain-core is not installed. Run: pip install langchain")

    model_lower = model.lower()

    if model_lower.startswith("gpt") or model_lower.startswith("o1") or model_lower.startswith("o3"):
        from langchain_openai import ChatOpenAI  # type: ignore[import]
        llm = ChatOpenAI(model=model, temperature=temperature)
    elif model_lower.startswith("claude"):
        from langchain_anthropic import ChatAnthropic  # type: ignore[import]
        llm = ChatAnthropic(model=model, temperature=temperature)
    elif model_lower.startswith("gemini"):
        from langchain_google_genai import ChatGoogleGenerativeAI  # type: ignore[import]
        llm = ChatGoogleGenerativeAI(model=model, temperature=temperature)
    else:
        # Fallback: assume OpenAI-compatible endpoint
        from langchain_openai import ChatOpenAI  # type: ignore[import]
        llm = ChatOpenAI(model=model, temperature=temperature)

    return llm.bind_tools(tools)


# ---------------------------------------------------------------------------
# Dialogue logging
# ---------------------------------------------------------------------------

def _write_dialogue(messages: list[Any], dialogue_path: str) -> None:
    """Persist LangGraph message history as dialogue.jsonl."""
    os.makedirs(os.path.dirname(dialogue_path), exist_ok=True)
    from datetime import datetime, timezone

    with open(dialogue_path, "w", encoding="utf-8") as f:
        for i, msg in enumerate(messages):
            if not _LANGCHAIN_AVAILABLE:
                content = str(msg)
                role = "unknown"
            else:
                content = msg.content if hasattr(msg, "content") else str(msg)
                role = type(msg).__name__.replace("Message", "").lower()
            entry = {
                "ts":      datetime.now(timezone.utc).isoformat(),
                "turn":    i,
                "role":    role,
                "type":    "message",
                "content": content if isinstance(content, str) else json.dumps(content),
            }
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# Node builders
# ---------------------------------------------------------------------------

def _build_role_node(
    role_name: str,
    role_config: RoleConfig,
    model: str,
    temperature: float,
):
    """Return a LangGraph node function for a TeamBench role.

    The node:
      1. Prepends the role's system_prompt to the conversation.
      2. Calls the LLM (with tools bound).
      3. Appends the response to state["messages"].
    """
    lc_tools = _langchain_tools_for_role(role_config)
    llm = _make_llm(model, temperature, lc_tools)
    system_msg = SystemMessage(content=role_config.system_prompt)  # type: ignore[name-defined]

    def node_fn(state: TeamBenchState) -> dict:
        msgs = [system_msg] + list(state["messages"])
        response = llm.invoke(msgs)
        return {"messages": state["messages"] + [response]}

    node_fn.__name__ = f"{role_name}_node"
    return node_fn, ToolNode(lc_tools)


# ---------------------------------------------------------------------------
# Conditional edge: did the verifier pass?
# ---------------------------------------------------------------------------

def _check_verdict(state: TeamBenchState) -> Literal["pass", "fail"]:
    """Read the last AIMessage to determine the verifier's verdict.

    The verifier is expected to output a JSON block containing
    {"verdict": "pass"} or {"verdict": "fail"}.  We also honour an explicit
    state["verdict"] if it was populated by the node.

    TODO: For more robust parsing, instruct the verifier to output ONLY
    a JSON object and parse state["attestation"] directly.
    """
    # Check state-level verdict first (populated by verifier node)
    if state.get("verdict") in ("pass", "fail"):
        return state["verdict"]  # type: ignore[return-value]

    # Fallback: scan the last assistant message for a verdict keyword
    for msg in reversed(state.get("messages", [])):
        if not _LANGCHAIN_AVAILABLE:
            break
        if not isinstance(msg, AIMessage):  # type: ignore[name-defined]
            continue
        content = msg.content if isinstance(msg.content, str) else ""
        if '"verdict": "pass"' in content or "'verdict': 'pass'" in content:
            return "pass"
        if '"verdict": "fail"' in content or "'verdict': 'fail'" in content:
            return "fail"
        break  # Only examine the most recent AI message

    return "fail"


def _should_remediate(state: TeamBenchState) -> str:
    """Conditional edge after verifier node.

    Returns "executor" to loop back for remediation, or "end" to finish.
    Caps remediation at 2 loops to avoid infinite cycles.
    """
    verdict = _check_verdict(state)
    if verdict == "pass":
        return END  # type: ignore[return-value]
    if state.get("remediation_count", 0) >= 2:
        return END  # type: ignore[return-value]
    return "executor"


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------

def _build_team_graph(
    roles: dict[str, RoleConfig],
    model: str,
    temperature: float,
) -> Any:
    """Construct the LangGraph StateGraph for the full team pipeline.

    Graph topology:
        START -> planner -> planner_tools -> executor -> executor_tools
              -> verifier -> verifier_tools
              -> (conditional) -> executor (remediation) | END
    """
    graph = StateGraph(TeamBenchState)

    # Build nodes for each role
    for role_name in ("planner", "executor", "verifier"):
        role_cfg = roles.get(role_name)
        if role_cfg is None:
            continue
        agent_node, tool_node = _build_role_node(role_name, role_cfg, model, temperature)
        graph.add_node(role_name, agent_node)
        graph.add_node(f"{role_name}_tools", tool_node)

        # Each agent node routes to its tool node when tool calls are present,
        # otherwise proceeds to the next role.
        # TODO: LangGraph >= 0.2 uses add_conditional_edges with a helper like
        # tools_condition.  Adjust the routing function if the API has changed.
        def _route_tools(state: TeamBenchState, _role=role_name) -> str:
            last_msg = state["messages"][-1] if state["messages"] else None
            if _LANGCHAIN_AVAILABLE and last_msg and isinstance(last_msg, AIMessage):  # type: ignore[name-defined]
                if getattr(last_msg, "tool_calls", None):
                    return f"{_role}_tools"
            # No tool calls — advance to next role
            next_role = {"planner": "executor", "executor": "verifier", "verifier": "__verdict__"}
            return next_role.get(_role, END)

        graph.add_conditional_edges(role_name, _route_tools)
        # Tool node always returns to its parent agent
        graph.add_edge(f"{role_name}_tools", role_name)

    # Entry point
    graph.set_entry_point("planner")

    # Verifier verdict routing — loop or end
    graph.add_conditional_edges(
        "verifier",
        _should_remediate,
        {
            "executor": "executor",
            END: END,
        },
    )

    return graph.compile()


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------

class LangGraphAdapter(TeamBenchFrameworkAdapter):
    """Run TeamBench tasks using LangGraph.

    Builds a StateGraph with planner/executor/verifier nodes connected by
    conditional edges.  The verifier node can loop back to the executor for
    remediation (up to max_remediations times) before the graph terminates.

    Args:
        model:              LLM model name (OpenAI, Anthropic, Gemini all supported).
        temperature:        Sampling temperature.
        max_turns:          Max messages before the graph forcibly terminates
                            (maps to LangGraph's recursion_limit).
        max_remediations:   Number of verifier->executor remediation loops allowed.
    """

    def __init__(
        self,
        model: str = "gpt-4o",
        temperature: float = 0.2,
        max_turns: int = 30,
        max_remediations: int = 2,
        **kwargs,
    ):
        if not _LANGGRAPH_AVAILABLE:
            raise ImportError(
                "LangGraph is not installed. Run: pip install langgraph langchain"
            )
        if not _LANGCHAIN_AVAILABLE:
            raise ImportError(
                "LangChain core is not installed. Run: pip install langchain"
            )
        self.model = model
        self.temperature = temperature
        self.max_turns = max_turns
        self.max_remediations = max_remediations

    # ------------------------------------------------------------------
    # TeamBenchFrameworkAdapter interface
    # ------------------------------------------------------------------

    def run_team(
        self,
        task_dir: str,
        run_dir: str,
        roles: dict[str, RoleConfig],
    ) -> FrameworkResult:
        """Run the full Planner -> Executor -> Verifier StateGraph."""
        paths = setup_run_directory(task_dir, run_dir)
        ctx = load_task_context(task_dir)
        dialogue_path = os.path.join(paths["messages"], "dialogue.jsonl")

        try:
            final_state = self._run_graph(ctx, paths, roles)
            _write_dialogue(final_state.get("messages", []), dialogue_path)
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
            metadata={
                "verdict":             final_state.get("verdict", "unknown"),
                "remediation_count":   final_state.get("remediation_count", 0),
                "message_count":       len(final_state.get("messages", [])),
            },
        )

    def run_single(
        self,
        task_dir: str,
        run_dir: str,
        role_config: RoleConfig,
    ) -> FrameworkResult:
        """Run a single-node StateGraph (oracle/restricted condition)."""
        paths = setup_run_directory(task_dir, run_dir)
        ctx = load_task_context(task_dir)
        dialogue_path = os.path.join(paths["messages"], "dialogue.jsonl")

        try:
            final_state = self._run_single_graph(ctx, paths, role_config)
            _write_dialogue(final_state.get("messages", []), dialogue_path)
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
            metadata={
                "verdict":       final_state.get("verdict", "unknown"),
                "message_count": len(final_state.get("messages", [])),
            },
        )

    # ------------------------------------------------------------------
    # Internal: graph execution
    # ------------------------------------------------------------------

    def _initial_state(self, ctx, paths: dict[str, str]) -> TeamBenchState:
        """Build the initial LangGraph state from task context."""
        task_id = os.path.basename(ctx.task_dir)
        initial_message = HumanMessage(  # type: ignore[name-defined]
            content=(
                f"Task: {task_id}\n\n"
                f"Specification:\n{ctx.spec}\n\n"
                f"Brief (Executor view):\n{ctx.brief}\n\n"
                "Planner: read the spec and send your plan.\n"
                "Executor: implement the solution in the workspace.\n"
                "Verifier: verify against the spec and write attestation.json.\n"
                "Output DONE when your role is complete."
            )
        )
        return TeamBenchState(
            messages=[initial_message],
            workspace_path=paths["workspace"],
            submission_path=paths["submission"],
            attestation={},
            verdict="pending",
            remediation_count=0,
        )

    def _run_graph(
        self,
        ctx,
        paths: dict[str, str],
        roles: dict[str, RoleConfig],
    ) -> dict:
        """Compile and invoke the full team graph."""
        graph = _build_team_graph(roles, self.model, self.temperature)
        initial_state = self._initial_state(ctx, paths)

        # TODO: LangGraph >= 0.2 supports streaming via graph.stream().
        # Use that for real-time logging of intermediate states.
        final_state = graph.invoke(
            initial_state,
            config={"recursion_limit": self.max_turns},
        )
        return final_state

    def _run_single_graph(
        self,
        ctx,
        paths: dict[str, str],
        role_config: RoleConfig,
    ) -> dict:
        """Build and run a minimal single-node graph."""
        # Single node: role -> role_tools -> END
        graph = StateGraph(TeamBenchState)

        agent_node, tool_node = _build_role_node(
            role_config.role, role_config, self.model, self.temperature
        )
        graph.add_node(role_config.role, agent_node)
        graph.add_node(f"{role_config.role}_tools", tool_node)

        def _route(state: TeamBenchState) -> str:
            last_msg = state["messages"][-1] if state["messages"] else None
            if _LANGCHAIN_AVAILABLE and last_msg and isinstance(last_msg, AIMessage):  # type: ignore[name-defined]
                if getattr(last_msg, "tool_calls", None):
                    return f"{role_config.role}_tools"
            return END

        graph.add_conditional_edges(role_config.role, _route)
        graph.add_edge(f"{role_config.role}_tools", role_config.role)
        graph.set_entry_point(role_config.role)

        compiled = graph.compile()
        task_id = os.path.basename(ctx.task_dir)
        initial_state = TeamBenchState(
            messages=[HumanMessage(content=(  # type: ignore[name-defined]
                f"Task: {task_id}\n\nSpec:\n{ctx.spec}\n\n"
                f"Workspace: {paths['workspace']}\n"
                f"Submission: {paths['submission']}\n"
                "Complete the task and write attestation.json. Output DONE when done."
            ))],
            workspace_path=paths["workspace"],
            submission_path=paths["submission"],
            attestation={},
            verdict="pending",
            remediation_count=0,
        )
        return compiled.invoke(
            initial_state,
            config={"recursion_limit": self.max_turns},
        )
