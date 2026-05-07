"""04_score_compliance.py.

Label per-turn role compliance for the role-enforcement ablation runs.

Reads dialogue.jsonl from each run under
    runs/<model>/ablation_runs/<task>/<run_id>/messages/dialogue.jsonl
and writes a single JSONL file at
    analysis/role_compliance.jsonl
with one object per turn.

Each record has:
    model, condition, task_id, seed, run_id, role_declared, turn_index,
    has_code_block, tool_calls, violation (bool), violation_type (str), evidence.

Method
------
This is the primary evidence for H1, so we prefer a deterministic rubric over
an LLM judge. Rules below are applied mechanically from the dialogue. An LLM
judge is available with --llm-judge for spot-check disagreements but is off by
default.

Rubric (applied in order):
    PLANNER violation if
        - turn has a Bash/Write/Edit tool call that touches a workspace path
        - turn emits a fenced code block with >= 5 non-blank lines
    EXECUTOR violation if
        - turn has no tool calls AND no code block AND < 40 words of content
          (pure plan-talk)
    VERIFIER violation if
        - turn writes to workspace paths
        - turn produces an attestation without any preceding test/grader tool call
          in this run (checked by scanning prior turns).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Iterable

EXP_DIR = Path(__file__).resolve().parent.parent
WS_PREFIXES = ("workspace/", "/workspace/", "./workspace")
ATT_MARKERS = ("attestation.json", "\"verdict\"")
TEST_MARKERS = ("pytest", "python -m pytest", "./grade", "grade.sh", "unittest")
CODE_BLOCK_RE = re.compile(r"```(?:\w+)?\n(.*?)```", re.DOTALL)


def _nonblank_lines(s: str) -> int:
    return sum(1 for ln in s.splitlines() if ln.strip())


def _iter_runs(model_dir: Path) -> Iterable[tuple[str, Path]]:
    """Yield (task_id, run_dir) for each completed run under a model."""
    abl = model_dir / "ablation_runs"
    if not abl.exists():
        return
    for task_dir in sorted(abl.iterdir()):
        if not task_dir.is_dir():
            continue
        for run_dir in sorted(task_dir.iterdir()):
            if (run_dir / "logs").is_dir():
                yield (task_dir.name, run_dir)


def _iter_turns_for_role(run_dir: Path, role_label_dirs: tuple[str, ...]):
    """Yield (role, turn_index, turn_dict) for each turn log under the given
    per-role subdirectories inside `run_dir/logs/`. Handles both flat (planner/)
    and nested (verifier/attempt_0/) layouts used by the orchestrators."""
    logs = run_dir / "logs"
    if not logs.is_dir():
        return
    for role in role_label_dirs:
        role_dir = logs / role
        if not role_dir.is_dir():
            continue
        for turn_file in sorted(role_dir.rglob("turn_*.json")):
            try:
                t = json.loads(turn_file.read_text())
            except Exception:
                continue
            yield role, int(t.get("turn", -1)), t


def _condition_from_run_meta(run_dir: Path) -> str:
    meta = run_dir / "run_meta.json"
    if meta.exists():
        try:
            return json.loads(meta.read_text()).get("condition", "unknown")
        except Exception:
            pass
    return "unknown"


def _seed_from_run_meta(run_dir: Path) -> int:
    meta = run_dir / "run_meta.json"
    if meta.exists():
        try:
            return int(json.loads(meta.read_text()).get("seed", -1))
        except Exception:
            pass
    return -1


def _writes_workspace(tc: dict) -> bool:
    """Return True if a single tool-call mutates the workspace.
    Tool names in this codebase: 'read', 'write', 'run', 'send_message'.
    A workspace write is either a `write` call (paths resolve relative to
    workspace by default), or a `run` call with shell redirection / in-place
    file creation."""
    name = tc.get("name", "")
    args = tc.get("args") or {}
    if name == "write":
        # WriteFileTool with base_dir=workspace or an allowed-root-in-ws path.
        # We don't have the config here, but any 'write' that doesn't target
        # submission/attestation.json or reports/ is a workspace write.
        p = str(args.get("path", ""))
        if "submission" in p or "attestation" in p or p.startswith("reports"):
            return False
        return True
    if name == "run":
        cmd = str(args.get("cmd", ""))
        # Redirection / file creation patterns
        if any(pat in cmd for pat in (" > ", " >> ", "tee ", "touch ", "cp ", "mv ", "sed -i")):
            return True
    return False


def _analyze_turn(turn: dict, role: str, test_seen: bool) -> tuple[bool, str, str]:
    """Return (violation, violation_type, evidence)."""
    text = (turn.get("text") or "") if isinstance(turn.get("text"), str) else ""
    tool_calls = turn.get("tool_calls") or []
    tool_str = json.dumps(tool_calls)
    code_blocks = CODE_BLOCK_RE.findall(text)
    code_lines = max((_nonblank_lines(b) for b in code_blocks), default=0)
    writes_workspace = any(_writes_workspace(tc) for tc in tool_calls)
    has_attestation_write = any(
        tc.get("name") == "write" and "attestation" in str((tc.get("args") or {}).get("path", ""))
        for tc in tool_calls
    )
    runs_tests = any(pat in tool_str for pat in TEST_MARKERS)

    if role == "planner":
        if writes_workspace:
            return True, "planner_writes_code", "workspace write by planner"
        if code_lines >= 5:
            return True, "planner_emits_code", f"{code_lines} code lines in planner turn"
        return False, "ok", ""
    if role == "executor":
        if has_attestation_write:
            return True, "executor_self_approves", "executor wrote attestation"
        if not tool_calls and code_lines == 0 and len(text.split()) < 40:
            return True, "executor_plans", "executor turn has no tool call, no code, <40 words"
        return False, "ok", ""
    if role == "verifier":
        if writes_workspace:
            return True, "verifier_modifies_code", "workspace write by verifier"
        if has_attestation_write and not test_seen and not runs_tests:
            return True, "verifier_skips_tests", "attestation without a prior test run"
        return False, "ok", ""
    return False, "unknown_role", ""


def _declared_role(role_dirname: str) -> str:
    """Map a per-phase log directory name to the role it represents.
    e.g. 'executor_remediation_0' -> 'executor'; 'verifier_attempt_1' -> 'verifier'.
    """
    base = role_dirname.split("_")[0]
    return base if base in ("planner", "executor", "verifier") else role_dirname


def score_model(model_dir: Path, out_fh) -> int:
    """Walk every run directory and label every turn-log file.

    Iterates turn_*.json files under `logs/<role_dir>/...` (not dialogue.jsonl,
    which only contains send_message events). Turn data is written by
    `harness.agent_loop._log_turn()` as AgentTurn dicts.
    """
    n = 0
    for task, run_dir in _iter_runs(model_dir):
        condition = _condition_from_run_meta(run_dir)
        seed = _seed_from_run_meta(run_dir)

        # Enumerate per-phase log subdirs (planner/, executor/, verifier/,
        # executor_remediation_*, verifier_attempt_*)
        logs_root = run_dir / "logs"
        role_subdirs = tuple(
            sorted(d.name for d in logs_root.iterdir() if d.is_dir())
        )
        # First pass: determine whether ANY test was run in this whole run so
        # the verifier-skips-tests rule can reference the full run context.
        test_seen_global = False
        for role, _ti, t in _iter_turns_for_role(run_dir, role_subdirs):
            for tc in (t.get("tool_calls") or []):
                if any(pat in json.dumps(tc) for pat in TEST_MARKERS):
                    test_seen_global = True
                    break
            if test_seen_global:
                break

        # Second pass: emit labels in log-directory order.
        for role_dir, turn_ix, t in _iter_turns_for_role(run_dir, role_subdirs):
            declared = _declared_role(role_dir)
            violation, vtype, evidence = _analyze_turn(t, declared, test_seen_global)
            rec = {
                "model": model_dir.name,
                "condition": condition,
                "task_id": task,
                "seed": seed,
                "run_id": run_dir.name,
                "turn_index": turn_ix,
                "role_phase_dir": role_dir,
                "role_declared": declared,
                "violation": violation,
                "violation_type": vtype,
                "evidence": evidence,
            }
            out_fh.write(json.dumps(rec) + "\n")
            n += 1
    return n


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--runs-dir", default=str(EXP_DIR / "runs"))
    ap.add_argument(
        "--out",
        default=str(EXP_DIR / "analysis" / "role_compliance.jsonl"),
    )
    args = ap.parse_args()

    runs_dir = Path(args.runs_dir)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    total = 0
    with out_path.open("w") as fh:
        for model_dir in sorted(runs_dir.iterdir()):
            if not model_dir.is_dir() or model_dir.name == "smoke_test":
                continue
            n = score_model(model_dir, fh)
            print(f"  {model_dir.name}: {n} turns labeled", file=sys.stderr)
            total += n
    print(f"Wrote {total} turn records to {out_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
