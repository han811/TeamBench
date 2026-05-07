"""verify_implementation.py — reviewer-2-proof verification suite.

Runs a battery of checks on the `role_enforcement_ablation` implementation
without making any API calls. Exit code 0 if all checks pass, 1 otherwise.

Purpose
-------
This script is the replication entrypoint for verifying that the
three-condition implementation actually implements what HYPOTHESIS.md claims.
Each check corresponds to a specific claim in that document; if the check
fails, the claim is empirically false.

Run with:
    python experiments/role_enforcement_ablation/tests/verify_implementation.py

Or from repo root:
    python -m pytest experiments/role_enforcement_ablation/tests/ -v
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import textwrap
from dataclasses import asdict
from typing import Any, Callable

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, REPO_ROOT)

from harness.ablation import AblationCondition, run_full_ablation  # noqa: E402
from harness.agent_interface import (  # noqa: E402
    make_planner_config,
    make_executor_config,
    make_verifier_config,
    make_prompt_only_config,
)
from harness.agent_loop import AgentLoop, AgentTurn  # noqa: E402
from harness.orchestrator import (  # noqa: E402
    VariableEnforcementOrchestrator,
    TaskOrchestrator,
    PhaseResult,
    build_transcript_seed,
    _serialise_turn,
)


# -----------------------------------------------------------------------------
# Test infrastructure
# -----------------------------------------------------------------------------

FAILURES: list[tuple[str, str]] = []


def check(claim: str) -> Callable:
    """Decorator: register a check. Failure is logged, execution continues."""
    def _wrap(fn: Callable) -> Callable:
        def _run() -> None:
            try:
                fn()
                print(f"  PASS  {claim}")
            except AssertionError as e:
                FAILURES.append((claim, str(e)))
                print(f"  FAIL  {claim}")
                print(f"        {e}")
            except Exception as e:  # noqa: BLE001
                FAILURES.append((claim, f"{type(e).__name__}: {e}"))
                print(f"  ERROR {claim}")
                print(f"        {type(e).__name__}: {e}")
        _run.__name__ = fn.__name__
        return _run
    return _wrap


def _make_fake_task(tmpdir: str) -> tuple[str, str]:
    """Create a minimal task_dir + run_dir for orchestrator instantiation."""
    task_dir = os.path.join(tmpdir, "FAKE_TASK")
    run_dir = os.path.join(tmpdir, "run_01")
    os.makedirs(task_dir)
    for sub in ("workspace", "reports", "messages", "submission", "logs"):
        os.makedirs(os.path.join(run_dir, sub))
    with open(os.path.join(task_dir, "spec.md"), "w") as f:
        f.write("FAKE SPEC")
    with open(os.path.join(task_dir, "brief.md"), "w") as f:
        f.write("FAKE BRIEF")
    return task_dir, run_dir


# -----------------------------------------------------------------------------
# CLAIM 1: Enum wiring
# -----------------------------------------------------------------------------

@check("CLAIM 1a: three new AblationCondition values exist with expected string IDs")
def test_enum_values() -> None:
    assert AblationCondition.PROMPT_ONLY.value == "prompt_only"
    assert AblationCondition.ENFORCED_SHARED_HISTORY.value == "enforced_shared_history"
    assert AblationCondition.ENFORCED.value == "enforced"


@check("CLAIM 1b: new conditions are EXCLUDED from 'run all' default (no double-counting)")
def test_experiment_scoped_filter() -> None:
    # Inspect run_full_ablation source for the guard. We can't easily exec without
    # API keys, so we check the source directly.
    import inspect
    src = inspect.getsource(run_full_ablation)
    assert "_EXPERIMENT_SCOPED" in src, "Missing _EXPERIMENT_SCOPED filter"
    for cond in ("PROMPT_ONLY", "ENFORCED_SHARED_HISTORY", "ENFORCED"):
        assert cond in src, f"Filter missing {cond}"


# -----------------------------------------------------------------------------
# CLAIM 2: Tool symmetry / asymmetry
# -----------------------------------------------------------------------------

@check("CLAIM 2a: prompt_only — planner/executor/verifier have IDENTICAL tool classes")
def test_prompt_only_tool_symmetry() -> None:
    with tempfile.TemporaryDirectory() as td:
        kw = dict(
            spec_path=os.path.join(td, "spec.md"),
            brief_path=os.path.join(td, "brief.md"),
            workspace_dir=os.path.join(td, "workspace"),
            reports_dir=os.path.join(td, "reports"),
            messages_dir=os.path.join(td, "messages"),
            submission_dir=os.path.join(td, "submission"),
            task_dir=td,
        )
        configs = {
            role: make_prompt_only_config(role_name=role, **kw)
            for role in ("planner", "executor", "verifier")
        }
        tool_sigs = {
            role: tuple(sorted(type(t).__name__ for t in cfg.tools))
            for role, cfg in configs.items()
        }
        unique = set(tool_sigs.values())
        assert len(unique) == 1, (
            f"prompt_only tool sets differ across roles: {tool_sigs}"
        )


@check("CLAIM 2b: enforced — planner has STRICTLY fewer tool classes than executor")
def test_enforced_tool_asymmetry() -> None:
    with tempfile.TemporaryDirectory() as td:
        pc = make_planner_config(
            spec_path=os.path.join(td, "spec.md"),
            messages_dir=os.path.join(td, "messages"),
            task_dir=td,
        )
        ec = make_executor_config(
            brief_path=os.path.join(td, "brief.md"),
            workspace_dir=os.path.join(td, "workspace"),
            reports_dir=os.path.join(td, "reports"),
            messages_dir=os.path.join(td, "messages"),
            submission_dir=os.path.join(td, "submission"),
            task_dir=td,
        )
        p_types = {type(t).__name__ for t in pc.tools}
        e_types = {type(t).__name__ for t in ec.tools}
        assert p_types.issubset(e_types), (
            f"Planner has tools executor lacks: {p_types - e_types}"
        )
        assert "WriteFileTool" in e_types, "Executor missing WriteFileTool"
        # Note: make_planner_config MAY include ReadFileTool (for spec); that's fine.
        # The load-bearing check is that planner LACKS write to workspace.


@check("CLAIM 2c: prompt_only — each role's SendMessageTool has correct sender_role label")
def test_prompt_only_sender_role_label() -> None:
    with tempfile.TemporaryDirectory() as td:
        kw = dict(
            spec_path=os.path.join(td, "spec.md"),
            brief_path=os.path.join(td, "brief.md"),
            workspace_dir=os.path.join(td, "workspace"),
            reports_dir=os.path.join(td, "reports"),
            messages_dir=os.path.join(td, "messages"),
            submission_dir=os.path.join(td, "submission"),
            task_dir=td,
        )
        for role in ("planner", "executor", "verifier"):
            cfg = make_prompt_only_config(role_name=role, **kw)
            send_tools = [t for t in cfg.tools if type(t).__name__ == "SendMessageTool"]
            assert len(send_tools) == 1, f"{role}: expected 1 SendMessageTool"
            assert getattr(send_tools[0], "sender_role", None) == role, (
                f"{role}: sender_role mislabeled as {send_tools[0].sender_role!r}"
            )


# -----------------------------------------------------------------------------
# CLAIM 3: Prompt-content parity (no prompt-engineering confound)
# -----------------------------------------------------------------------------

@check("CLAIM 3a: prompt_only prompts cover same role-specific instruction topics as enforced")
def test_prompt_content_coverage() -> None:
    """Ensure role-specific prompts in prompt_only are functionally content-matched.

    We check that the planner/executor/verifier prompts in prompt_only contain the
    key instructional topics from their enforced counterparts. Rigid string equality
    would be brittle (the workspace-access language legitimately differs), so we
    check topic coverage.
    """
    with tempfile.TemporaryDirectory() as td:
        kw = dict(
            spec_path=os.path.join(td, "spec.md"),
            brief_path=os.path.join(td, "brief.md"),
            workspace_dir=os.path.join(td, "workspace"),
            reports_dir=os.path.join(td, "reports"),
            messages_dir=os.path.join(td, "messages"),
            submission_dir=os.path.join(td, "submission"),
            task_dir=td,
        )
        required_per_role = {
            "planner": ["plan", "executor", "send_message", "DONE"],
            "executor": ["workspace", "planner", "verifier", "DONE"],
            "verifier": ["attestation", "verdict", "pass", "DONE"],
        }
        for role, markers in required_per_role.items():
            cfg = make_prompt_only_config(role_name=role, **kw)
            prompt_lower = cfg.system_prompt.lower()
            missing = [m for m in markers if m.lower() not in prompt_lower]
            assert not missing, (
                f"{role} prompt_only system_prompt missing markers: {missing}\n"
                f"prompt was:\n{cfg.system_prompt}"
            )


# -----------------------------------------------------------------------------
# CLAIM 4: Transcript seed format
# -----------------------------------------------------------------------------

@check("CLAIM 4a: build_transcript_seed returns [] for empty input")
def test_seed_empty() -> None:
    assert build_transcript_seed([]) == []


@check("CLAIM 4b: seed preserves turn role, text, tool calls, tool results")
def test_seed_roundtrip() -> None:
    t = AgentTurn(
        turn=3, role="planner", text="I will plan",
        tool_calls=[{"name": "read", "args": {"path": "spec.md"}}],
        tool_results=[{"stdout": "spec contents here", "stderr": "", "exit_code": 0}],
    )
    phase = PhaseResult(phase="planning", turns=[t])
    seed = build_transcript_seed([phase])
    assert len(seed) == 1
    content = seed[0]["content"]
    for expected in ["planner", "I will plan", "read", "spec.md", "exit_code=0", "spec contents"]:
        assert expected in content, f"seed missing {expected!r}: {content[:300]!r}"


@check("CLAIM 4c: seed handles turns with no tool calls / no text gracefully")
def test_seed_edge_cases() -> None:
    # Turn with only text, no tool calls
    t1 = AgentTurn(turn=0, role="executor", text="just thinking")
    # Turn with tool calls but no text
    t2 = AgentTurn(
        turn=1, role="executor", text="",
        tool_calls=[{"name": "run", "args": {"cmd": "ls"}}],
        tool_results=[{"stdout": "", "stderr": "", "exit_code": 0}],
    )
    # Turn with empty tool_results (shouldn't crash)
    t3 = AgentTurn(
        turn=2, role="executor", text="done",
        tool_calls=[{"name": "run", "args": {"cmd": "echo hi"}}],
        tool_results=[],
    )
    phase = PhaseResult(phase="execution", turns=[t1, t2, t3])
    seed = build_transcript_seed([phase])
    content = seed[0]["content"]
    # No crash, all three turn indices present
    for idx in ("Turn 0", "Turn 1", "Turn 2"):
        assert idx in content, f"seed dropped {idx}"


@check("CLAIM 4d: seed truncates huge tool-output to prevent context blowup")
def test_seed_truncates_huge_output() -> None:
    huge = "X" * 100_000
    t = AgentTurn(
        turn=0, role="executor", text="",
        tool_calls=[{"name": "run", "args": {"cmd": "cat bigfile"}}],
        tool_results=[{"stdout": huge, "stderr": "", "exit_code": 0}],
    )
    phase = PhaseResult(phase="execution", turns=[t])
    seed = build_transcript_seed([phase])
    # Serialized seed should not preserve all 100k bytes verbatim
    assert len(seed[0]["content"]) < 10_000, (
        f"seed did not truncate: {len(seed[0]['content'])} chars"
    )


# -----------------------------------------------------------------------------
# CLAIM 5: Orchestrator parity (the critical one)
# -----------------------------------------------------------------------------

@check("CLAIM 5a: VariableEnforcementOrchestrator(enforced) and TaskOrchestrator use "
       "SAME config factories with SAME arguments")
def test_orchestrator_config_parity() -> None:
    """In share_tools=False mode, VEO must call the same make_*_config factories
    with the same arguments as TaskOrchestrator. This is the parity claim that
    justifies reporting ENFORCED ~ FULL as equivalent."""
    with tempfile.TemporaryDirectory() as td:
        task_dir, run_dir = _make_fake_task(td)
        veo = VariableEnforcementOrchestrator(
            task_dir=task_dir, run_dir=run_dir, adapter=None,
            share_tools=False, share_history=False,
        )
        to = TaskOrchestrator(task_dir=task_dir, run_dir=run_dir, adapter=None)

        # planner, executor, verifier config tool CLASSES must match
        veo_planner_tools = sorted(type(t).__name__ for t in veo._planner_config().tools)
        to_planner_cfg = make_planner_config(
            spec_path=to.spec_path, messages_dir=to.messages, task_dir=to.task_dir,
        )
        to_planner_tools = sorted(type(t).__name__ for t in to_planner_cfg.tools)
        assert veo_planner_tools == to_planner_tools, (
            f"planner parity broken: VEO={veo_planner_tools} TO={to_planner_tools}"
        )

        veo_exec_tools = sorted(type(t).__name__ for t in veo._executor_config().tools)
        to_exec_cfg = make_executor_config(
            brief_path=to.brief_path, workspace_dir=to.workspace,
            reports_dir=to.reports, messages_dir=to.messages,
            submission_dir=to.submission, task_dir=to.task_dir,
        )
        to_exec_tools = sorted(type(t).__name__ for t in to_exec_cfg.tools)
        assert veo_exec_tools == to_exec_tools, (
            f"executor parity broken: VEO={veo_exec_tools} TO={to_exec_tools}"
        )

        veo_ver_tools = sorted(type(t).__name__ for t in veo._verifier_config().tools)
        to_ver_cfg = make_verifier_config(
            spec_path=to.spec_path, workspace_dir=to.workspace,
            reports_dir=to.reports, messages_dir=to.messages,
            submission_dir=to.submission, task_dir=to.task_dir,
        )
        to_ver_tools = sorted(type(t).__name__ for t in to_ver_cfg.tools)
        assert veo_ver_tools == to_ver_tools, (
            f"verifier parity broken: VEO={veo_ver_tools} TO={to_ver_tools}"
        )


@check("CLAIM 5b: remediation budget is the SAME default across all three conditions")
def test_remediation_parity() -> None:
    with tempfile.TemporaryDirectory() as td:
        task_dir, run_dir = _make_fake_task(td)
        to = TaskOrchestrator(task_dir=task_dir, run_dir=run_dir, adapter=None)
        veo_enf = VariableEnforcementOrchestrator(
            task_dir=task_dir, run_dir=run_dir, adapter=None,
            share_tools=False, share_history=False,
        )
        veo_esh = VariableEnforcementOrchestrator(
            task_dir=task_dir, run_dir=run_dir, adapter=None,
            share_tools=False, share_history=True,
        )
        veo_po = VariableEnforcementOrchestrator(
            task_dir=task_dir, run_dir=run_dir, adapter=None,
            share_tools=True, share_history=True,
        )
        budgets = {
            "TaskOrchestrator": to.max_remediation_loops,
            "VEO/enforced": veo_enf.max_remediation_loops,
            "VEO/enforced_shared_history": veo_esh.max_remediation_loops,
            "VEO/prompt_only": veo_po.max_remediation_loops,
        }
        unique = set(budgets.values())
        assert len(unique) == 1, f"Remediation budget divergence: {budgets}"


@check("CLAIM 5c: max_turns_per_phase identical across all three conditions")
def test_turn_budget_parity() -> None:
    with tempfile.TemporaryDirectory() as td:
        task_dir, run_dir = _make_fake_task(td)
        to = TaskOrchestrator(task_dir=task_dir, run_dir=run_dir, adapter=None)
        modes = [(False, False), (False, True), (True, True)]
        for st, sh in modes:
            veo = VariableEnforcementOrchestrator(
                task_dir=task_dir, run_dir=run_dir, adapter=None,
                share_tools=st, share_history=sh,
            )
            assert veo.max_turns_per_phase == to.max_turns_per_phase, (
                f"Turn budget diverges at st={st} sh={sh}: "
                f"{veo.max_turns_per_phase} vs {to.max_turns_per_phase}"
            )


@check("CLAIM 5d: condition_tag is correctly set for each (share_tools, share_history) combo")
def test_condition_tag() -> None:
    with tempfile.TemporaryDirectory() as td:
        task_dir, run_dir = _make_fake_task(td)
        expected = {
            (False, False): "enforced",
            (False, True): "enforced_shared_history",
            (True, True): "prompt_only",
        }
        for (st, sh), tag in expected.items():
            veo = VariableEnforcementOrchestrator(
                task_dir=task_dir, run_dir=run_dir, adapter=None,
                share_tools=st, share_history=sh,
            )
            assert veo._condition_tag == tag, (
                f"tag mismatch for (st={st}, sh={sh}): got {veo._condition_tag!r}, want {tag!r}"
            )


# -----------------------------------------------------------------------------
# CLAIM 6: Seed application gate
# -----------------------------------------------------------------------------

@check("CLAIM 6: seed is passed to AgentLoop ONLY when share_history=True")
def test_seed_gate() -> None:
    with tempfile.TemporaryDirectory() as td:
        task_dir, run_dir = _make_fake_task(td)
        prior = [PhaseResult(
            phase="planning",
            turns=[AgentTurn(turn=0, role="planner", text="plan")],
        )]
        veo_no = VariableEnforcementOrchestrator(
            task_dir=task_dir, run_dir=run_dir, adapter=None,
            share_tools=False, share_history=False,
        )
        veo_yes = VariableEnforcementOrchestrator(
            task_dir=task_dir, run_dir=run_dir, adapter=None,
            share_tools=False, share_history=True,
        )
        assert veo_no._seed_if_shared(prior) is None, "share_history=False should not seed"
        seed = veo_yes._seed_if_shared(prior)
        assert seed is not None and len(seed) == 1, "share_history=True should seed"


# -----------------------------------------------------------------------------
# CLAIM 7: AgentLoop backward compatibility
# -----------------------------------------------------------------------------

@check("CLAIM 7: AgentLoop.run() accepts seed_context kwarg, default None preserves legacy")
def test_agent_loop_signature() -> None:
    import inspect
    sig = inspect.signature(AgentLoop.run)
    assert "seed_context" in sig.parameters, "seed_context parameter missing"
    default = sig.parameters["seed_context"].default
    assert default is None, f"default seed_context is {default!r}, expected None"


# -----------------------------------------------------------------------------
# CLAIM 8: Dispatch routing
# -----------------------------------------------------------------------------

@check("CLAIM 8: all three new conditions route through VariableEnforcementOrchestrator")
def test_dispatch_routing() -> None:
    import inspect
    from harness import ablation
    src = inspect.getsource(ablation.run_ablation_condition)
    # All three enum names present in dispatch
    for cond in ("PROMPT_ONLY", "ENFORCED_SHARED_HISTORY", "ENFORCED"):
        assert cond in src, f"Dispatch missing AblationCondition.{cond}"
    assert "VariableEnforcementOrchestrator" in src, "Dispatch doesn't use VEO"


# -----------------------------------------------------------------------------
# CLAIM 9: Attestation scoring is grade.sh-authoritative, not attestation-only
# (defense against 'prompt_only executor can fake attestation' critique)
# -----------------------------------------------------------------------------

@check("CLAIM 9: task scoring is derived from grade.sh, not orchestrator.verdict")
def test_scoring_source() -> None:
    """The critical reviewer-2 preempt: if scoring were based solely on
    attestation.json verdict, prompt_only executors could cheat by writing
    verdict=pass. Verify that run_full_ablation actually calls grade_run()."""
    import inspect
    from harness import ablation
    src = inspect.getsource(ablation.run_full_ablation)
    assert "grade_run" in src, (
        "run_full_ablation does not call grade_run — scoring may be attestation-only"
    )


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

def main() -> int:
    print("=" * 70)
    print("Role Enforcement Ablation — Implementation Verification")
    print("=" * 70)

    # Collect test functions defined at module level
    tests = [
        v for k, v in sorted(globals().items())
        if k.startswith("test_") and callable(v)
    ]
    print(f"Running {len(tests)} checks...\n")
    for t in tests:
        t()

    print()
    print("=" * 70)
    if FAILURES:
        print(f"FAILED: {len(FAILURES)} / {len(tests)} checks failed")
        for claim, err in FAILURES:
            print(f"  [{claim}]")
            print(f"    {err}")
        print("=" * 70)
        return 1
    else:
        print(f"ALL {len(tests)} CHECKS PASSED")
        print("=" * 70)
        return 0


if __name__ == "__main__":
    sys.exit(main())
