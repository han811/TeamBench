#!/usr/bin/env python3
"""
Run TeamBench tasks with an external multi-agent framework.

Usage:
    python scripts/run_with_framework.py \\
        --framework autogen \\
        --model gpt-4o \\
        --tasks MULTI1_fullstack_fix TEST1_spec_to_tests

    python scripts/run_with_framework.py \\
        --framework langgraph \\
        --model claude-opus-4-5 \\
        --tasks ALL \\
        --condition full \\
        --seeds 0 1 2

    python scripts/run_with_framework.py \\
        --framework crewai \\
        --model openai/gpt-4o \\
        --tasks CROSS1_api_contract \\
        --output shared/crewai_results.json

Supported frameworks:  native, autogen, crewai, langgraph
Supported conditions:  full (team), oracle (single agent with full spec + all tools)

The script mirrors the interface of harness/run_all.py so results can be
compared directly with native harness runs.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import traceback
from datetime import datetime, timezone

# Ensure the repo root is on the path regardless of where the script is called from
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _discover_tasks(tasks_dir: str) -> list[str]:
    """Return sorted list of task directory names found in tasks_dir."""
    if not os.path.isdir(tasks_dir):
        raise FileNotFoundError(f"Tasks directory not found: {tasks_dir}")
    return sorted(
        d for d in os.listdir(tasks_dir)
        if os.path.isdir(os.path.join(tasks_dir, d))
        and os.path.isfile(os.path.join(tasks_dir, d, "grade.sh"))
    )


def _make_run_dir(runs_dir: str, task_name: str, framework: str, seed: int) -> str:
    """Create and return a unique run directory path."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    run_id = f"{framework}_{ts}_seed{seed}"
    run_dir = os.path.join(runs_dir, task_name, run_id)
    os.makedirs(run_dir, exist_ok=True)
    return run_dir


def _write_run_meta(run_dir: str, meta: dict) -> None:
    with open(os.path.join(run_dir, "run_meta.json"), "w") as f:
        json.dump(meta, f, indent=2)


def _build_roles_for_condition(
    task_name: str,
    task_dir: str,
    run_dir: str,
    condition: str,
) -> tuple[dict, bool]:
    """Return (roles dict, is_team).

    For 'full': build planner + executor + verifier roles.
    For 'oracle': build a single oracle role with full access.
    """
    from harness.framework_adapter import build_team_roles, setup_run_directory
    from harness.agent_interface import (
        make_planner_config,
        make_executor_config,
        make_verifier_config,
        RoleConfig,
        RunCommandTool,
        ReadFileTool,
        WriteFileTool,
        SendMessageTool,
        _build_path_map,
    )

    paths = setup_run_directory(task_dir, run_dir)

    if condition == "full":
        roles = build_team_roles(task_dir, run_dir)
        return roles, True

    if condition == "oracle":
        # Oracle: single agent with full spec + all tools (no role restrictions)
        spec_path  = os.path.join(task_dir, "spec.md")
        workspace  = paths["workspace"]
        reports    = paths["reports"]
        messages   = paths["messages"]
        submission = paths["submission"]
        pm = _build_path_map(
            workspace_dir=workspace,
            reports_dir=reports,
            messages_dir=messages,
            submission_dir=submission,
            task_dir=os.path.abspath(task_dir),
        )
        oracle_config = RoleConfig(
            role="oracle",
            system_prompt=(
                "You are a senior software engineer completing a task autonomously.\n"
                "You have access to the full specification and can read/write workspace files "
                "and execute commands.\n"
                "Complete the task fully: implement the solution, then verify it against the spec.\n"
                "Write attestation.json to the submission directory when done.\n"
                "Output DONE when complete."
            ),
            tools=[
                RunCommandTool(cwd=workspace, allowed=True),
                ReadFileTool(
                    allowed_roots=[
                        os.path.dirname(spec_path), workspace, reports, messages, submission,
                    ],
                    path_map=pm,
                    base_dir=workspace,
                ),
                WriteFileTool(
                    allowed_roots=[workspace, reports, submission],
                    path_map=pm,
                    base_dir=workspace,
                ),
                SendMessageTool(messages_dir=messages, sender_role="oracle"),
            ],
        )
        return {"oracle": oracle_config}, False

    raise ValueError(f"Unknown condition '{condition}'. Choose from: full, oracle")


# ---------------------------------------------------------------------------
# Per-task runner
# ---------------------------------------------------------------------------

def run_one_task(
    task_name: str,
    task_dir: str,
    framework: str,
    model: str,
    condition: str,
    seed: int,
    runs_dir: str,
    temperature: float,
    max_turns: int,
    framework_kwargs: dict,
) -> dict:
    """Run a single task with the given framework and return a result dict."""
    from harness.frameworks import create_framework_adapter
    from harness.framework_adapter import grade_framework_result

    run_dir = _make_run_dir(runs_dir, task_name, framework, seed)
    _write_run_meta(run_dir, {
        "task_name": task_name,
        "framework": framework,
        "model":     model,
        "condition": condition,
        "seed":      seed,
    })

    print(f"\n[{framework}] {task_name} | condition={condition} seed={seed}")
    print(f"  run_dir: {run_dir}")

    t0 = time.time()
    result = {
        "task_name": task_name,
        "framework": framework,
        "model":     model,
        "condition": condition,
        "seed":      seed,
        "run_dir":   run_dir,
        "score":     None,
        "error":     None,
        "duration_s": 0.0,
    }

    try:
        adapter = create_framework_adapter(
            framework,
            model=model,
            temperature=temperature,
            max_turns=max_turns,
            **framework_kwargs,
        )
        roles, is_team = _build_roles_for_condition(task_name, task_dir, run_dir, condition)

        if is_team:
            fw_result = adapter.run_team(task_dir, run_dir, roles)
        else:
            # Oracle / single-agent condition
            role_config = list(roles.values())[0]
            fw_result = adapter.run_single(task_dir, run_dir, role_config)

        if not fw_result.success:
            result["error"] = fw_result.error or "framework reported failure"
            print(f"  ERROR: {result['error']}")
        else:
            score = grade_framework_result(fw_result, task_name, task_dir)
            result["score"] = score
            passed = score.get("pass", False)
            primary = score.get("primary", {}).get("success", 0)
            print(f"  pass={passed}  primary={primary}")

    except Exception:
        tb = traceback.format_exc()
        result["error"] = tb
        print(f"  EXCEPTION:\n{tb}")

    result["duration_s"] = round(time.time() - t0, 2)
    return result


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Run TeamBench tasks with an external multi-agent framework.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument(
        "--framework",
        required=True,
        choices=["native", "autogen", "crewai", "langgraph"],
        help="Framework adapter to use.",
    )
    p.add_argument(
        "--model",
        required=True,
        help="LLM model name (e.g. gpt-4o, claude-opus-4-5, gemini-3-flash-preview).",
    )
    p.add_argument(
        "--tasks",
        nargs="+",
        default=["ALL"],
        metavar="TASK",
        help="Task name(s) to run, or ALL to run every task in --tasks_dir.",
    )
    p.add_argument(
        "--tasks_dir",
        default="tasks",
        help="Root directory containing task sub-directories (default: tasks/).",
    )
    p.add_argument(
        "--runs_dir",
        default="shared/framework_runs",
        help="Directory to write run outputs (default: shared/framework_runs/).",
    )
    p.add_argument(
        "--output",
        default=None,
        help="Path to write JSON results summary (default: shared/framework_runs/<framework>_results.json).",
    )
    p.add_argument(
        "--condition",
        default="full",
        choices=["full", "oracle"],
        help="Ablation condition: full (team) or oracle (single agent). Default: full.",
    )
    p.add_argument(
        "--seeds",
        nargs="+",
        type=int,
        default=[0],
        metavar="SEED",
        help="Seeds to evaluate (default: 0).",
    )
    p.add_argument(
        "--temperature",
        type=float,
        default=0.2,
        help="Sampling temperature (default: 0.2).",
    )
    p.add_argument(
        "--max_turns",
        type=int,
        default=30,
        help="Maximum agent turns per role (default: 30).",
    )
    p.add_argument(
        "--api_key",
        default=None,
        help="Optional API key override (falls back to env vars).",
    )
    p.add_argument(
        "--base_url",
        default=None,
        help="Optional API base URL (for vLLM / Azure / proxy endpoints).",
    )
    p.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose framework output (CrewAI / LangGraph streaming).",
    )
    return p.parse_args()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    args = _parse_args()

    # Resolve paths relative to repo root
    tasks_dir = os.path.join(_REPO_ROOT, args.tasks_dir)
    runs_dir  = os.path.join(_REPO_ROOT, args.runs_dir)
    os.makedirs(runs_dir, exist_ok=True)

    # Resolve task list
    if args.tasks == ["ALL"]:
        task_names = _discover_tasks(tasks_dir)
        print(f"Discovered {len(task_names)} tasks in {tasks_dir}")
    else:
        task_names = args.tasks

    # Validate task directories exist
    valid_tasks = []
    for t in task_names:
        td = os.path.join(tasks_dir, t)
        if not os.path.isdir(td):
            print(f"WARNING: Task directory not found, skipping: {td}")
            continue
        if not os.path.isfile(os.path.join(td, "grade.sh")):
            print(f"WARNING: No grade.sh found, skipping: {t}")
            continue
        valid_tasks.append(t)

    if not valid_tasks:
        print("ERROR: No valid tasks found. Exiting.")
        sys.exit(1)

    print(f"\nRunning {len(valid_tasks)} task(s) x {len(args.seeds)} seed(s) "
          f"with framework={args.framework}, model={args.model}, condition={args.condition}\n")

    # Extra kwargs passed through to the framework adapter
    framework_kwargs: dict = {}
    if args.api_key:
        framework_kwargs["api_key"] = args.api_key
    if args.base_url:
        framework_kwargs["base_url"] = args.base_url
    if args.verbose:
        framework_kwargs["verbose"] = True

    # Run all tasks
    all_results: list[dict] = []
    for task_name in valid_tasks:
        task_dir = os.path.join(tasks_dir, task_name)
        for seed in args.seeds:
            res = run_one_task(
                task_name=task_name,
                task_dir=task_dir,
                framework=args.framework,
                model=args.model,
                condition=args.condition,
                seed=seed,
                runs_dir=runs_dir,
                temperature=args.temperature,
                max_turns=args.max_turns,
                framework_kwargs=framework_kwargs,
            )
            all_results.append(res)

    # Summary statistics
    scored   = [r for r in all_results if r["score"] is not None]
    passed   = [r for r in scored if r["score"].get("pass", False)]
    errored  = [r for r in all_results if r["error"]]
    pass_rate = len(passed) / len(scored) if scored else 0.0

    print(f"\n{'='*60}")
    print(f"Framework:  {args.framework}")
    print(f"Model:      {args.model}")
    print(f"Condition:  {args.condition}")
    print(f"Tasks run:  {len(all_results)}")
    print(f"Scored:     {len(scored)}")
    print(f"Passed:     {len(passed)}")
    print(f"Pass rate:  {pass_rate:.1%}")
    print(f"Errors:     {len(errored)}")
    print(f"{'='*60}\n")

    summary = {
        "framework":  args.framework,
        "model":      args.model,
        "condition":  args.condition,
        "seeds":      args.seeds,
        "tasks_run":  len(all_results),
        "scored":     len(scored),
        "passed":     len(passed),
        "pass_rate":  pass_rate,
        "errors":     len(errored),
        "results":    all_results,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    # Write output
    output_path = args.output or os.path.join(
        _REPO_ROOT, "shared", "framework_runs",
        f"{args.framework}_{args.condition}_results.json",
    )
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"Results written to: {output_path}")


if __name__ == "__main__":
    main()
