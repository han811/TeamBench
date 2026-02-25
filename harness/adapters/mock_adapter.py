"""
Mock adapter for end-to-end pipeline testing without API keys.

The MockAdapter simulates a competent agent team by reading expected.json
and producing tool calls that write the correct output. This lets us:
1. Verify the full Orchestrator -> AgentLoop -> Grader pipeline works
2. Confirm graders pass when correct output is produced
3. Test seed-aware generation + grading without spending API tokens

Usage:
    adapter = MockAdapter(reports_dir="/path/to/reports")
    # Pass to TaskOrchestrator or ablation framework
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

from harness.agent_interface import AdapterResponse, ToolCallAdapter


class MockAdapter(ToolCallAdapter):
    """Deterministic adapter that solves tasks by reading expected.json.

    Behavior per role (detected from system_prompt):
    - Planner: reads spec, sends plan to executor via send_message
    - Executor: reads expected.json, writes correct output files
    - Verifier: reads workspace, writes passing attestation
    - Oracle/Restricted: combines executor + verifier behavior
    """

    def __init__(self, reports_dir: str = "", temperature: float = 0.0):
        self.reports_dir = reports_dir
        self.model = "mock-adapter"
        self._usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
        self._turn_count = 0

    def generate_with_tools(
        self,
        messages: list[dict],
        system_prompt: str,
        tools: list[dict],
    ) -> AdapterResponse:
        self._turn_count += 1
        self._usage["input_tokens"] += 100
        self._usage["output_tokens"] += 50
        self._usage["total_tokens"] += 150

        # Detect role from system prompt
        sp_lower = system_prompt.lower()
        is_planner = "planner" in sp_lower and "executor" not in sp_lower
        is_executor = "executor" in sp_lower
        is_verifier = "verifier" in sp_lower and "executor" not in sp_lower
        is_oracle = "oracle" in sp_lower
        is_restricted = "restricted" in sp_lower

        # Check if this is a tool result turn (means we already acted)
        last_msg = messages[-1]["content"] if messages else ""
        if "Tool '" in last_msg or "result:" in last_msg:
            return AdapterResponse(text="DONE", tool_calls=[], done=True)

        tool_names = {t["name"] for t in tools}

        if is_planner:
            return self._planner_response(messages, tool_names)
        elif is_executor or is_restricted:
            return self._executor_response(messages, tool_names)
        elif is_verifier:
            return self._verifier_response(messages, tool_names)
        elif is_oracle:
            return self._oracle_response(messages, tool_names)
        else:
            return AdapterResponse(text="DONE", tool_calls=[], done=True)

    def _planner_response(self, messages: list[dict], tool_names: set) -> AdapterResponse:
        """Planner: read spec and send plan to executor."""
        # First turn: read spec
        if self._turn_count <= 1 and "read" in tool_names:
            return AdapterResponse(
                text="Reading spec...",
                tool_calls=[{"name": "read", "args": {"path": "spec.md"}}],
            )

        # Second turn: send plan to executor
        if "send_message" in tool_names:
            # Extract expected.json path hint from messages
            plan_text = (
                "Plan: Follow the specification exactly. "
                "Read expected.json from reports for the correct values. "
                "Write all required output files."
            )
            return AdapterResponse(
                text="Sending plan...",
                tool_calls=[{
                    "name": "send_message",
                    "args": {"to": "executor", "content": plan_text},
                }],
            )

        return AdapterResponse(text="DONE", tool_calls=[], done=True)

    def _executor_response(self, messages: list[dict], tool_names: set) -> AdapterResponse:
        """Executor: read expected.json, write correct output."""
        # First turn: read expected.json
        if self._turn_count <= 1 and "read" in tool_names:
            return AdapterResponse(
                text="Reading expected output...",
                tool_calls=[{"name": "read", "args": {"path": "/shared/reports/expected.json"}}],
            )

        # Second turn: parse expected and write files
        expected = self._extract_expected(messages)
        if expected and "write" in tool_names:
            tool_calls = self._build_write_calls(expected)
            if tool_calls:
                return AdapterResponse(text="Writing output...", tool_calls=tool_calls)

        # Notify verifier
        if "send_message" in tool_names:
            return AdapterResponse(
                text="Work complete.",
                tool_calls=[{
                    "name": "send_message",
                    "args": {"to": "verifier", "content": "Work complete."},
                }],
            )

        return AdapterResponse(text="DONE", tool_calls=[], done=True)

    def _verifier_response(self, messages: list[dict], tool_names: set) -> AdapterResponse:
        """Verifier: write passing attestation."""
        if "write" in tool_names:
            # Extract task_id from messages
            task_id = self._extract_task_id(messages)
            attestation = json.dumps({
                "task_id": task_id,
                "verdict": "pass",
                "checklist": [
                    {"id": "req_all", "ok": True, "note": "All requirements verified"}
                ],
            })
            return AdapterResponse(
                text="Verification complete.",
                tool_calls=[{
                    "name": "write",
                    "args": {"path": "attestation.json", "content": attestation},
                }],
            )
        return AdapterResponse(text="DONE", tool_calls=[], done=True)

    def _oracle_response(self, messages: list[dict], tool_names: set) -> AdapterResponse:
        """Oracle: read expected, write output + attestation."""
        if self._turn_count <= 1 and "read" in tool_names:
            return AdapterResponse(
                text="Reading expected...",
                tool_calls=[{"name": "read", "args": {"path": "/shared/reports/expected.json"}}],
            )

        expected = self._extract_expected(messages)
        calls = []
        if expected and "write" in tool_names:
            calls = self._build_write_calls(expected)

        task_id = self._extract_task_id(messages)
        attestation = json.dumps({
            "task_id": task_id,
            "verdict": "pass",
            "checklist": [],
        })
        calls.append({
            "name": "write",
            "args": {"path": "attestation.json", "content": attestation},
        })
        return AdapterResponse(text="Oracle complete.", tool_calls=calls)

    def _extract_expected(self, messages: list[dict]) -> dict | None:
        """Extract expected.json content from message history."""
        for msg in reversed(messages):
            content = msg.get("content", "")
            # Look for JSON content from a read tool result
            if "expected.json" in content or "correct_config" in content:
                # Try to find JSON in the content
                for line in content.split("\n"):
                    line = line.strip()
                    if line.startswith("{"):
                        try:
                            return json.loads(line)
                        except json.JSONDecodeError:
                            pass
                # Try parsing the whole stdout section
                if "stdout:" in content:
                    stdout_start = content.index("stdout:") + 7
                    rest = content[stdout_start:].strip()
                    # Find the JSON blob
                    if rest.startswith("{"):
                        depth = 0
                        for i, ch in enumerate(rest):
                            if ch == "{":
                                depth += 1
                            elif ch == "}":
                                depth -= 1
                                if depth == 0:
                                    try:
                                        return json.loads(rest[: i + 1])
                                    except json.JSONDecodeError:
                                        break

        # Fallback: try to read from reports_dir directly
        if self.reports_dir:
            exp_path = os.path.join(self.reports_dir, "expected.json")
            if os.path.isfile(exp_path):
                with open(exp_path, "r") as f:
                    return json.load(f)
        return None

    def _build_write_calls(self, expected: dict) -> list[dict]:
        """Build write tool calls from expected.json structure."""
        calls = []

        # P1: correct_config -> output/config.json
        if "correct_config" in expected:
            calls.append({
                "name": "write",
                "args": {
                    "path": "output/config.json",
                    "content": json.dumps(expected["correct_config"], indent=2),
                },
            })

        # P2: resolved_config -> output/resolved_config.json
        if "resolved_config" in expected:
            calls.append({
                "name": "write",
                "args": {
                    "path": "output/resolved_config.json",
                    "content": json.dumps(expected["resolved_config"], indent=2),
                },
            })

        # IR1/IR2: answer -> answer.json
        if "answer" in expected and "evidence" not in expected.get("correct_config", {}):
            answer_obj = {"answer": expected["answer"]}
            if "correct_evidence" in expected:
                answer_obj["evidence"] = expected["correct_evidence"]
            calls.append({
                "name": "write",
                "args": {
                    "path": "output/answer.json",
                    "content": json.dumps(answer_obj, indent=2),
                },
            })

        # D1: expected has correct_schema, correct_data
        if "correct_schema" in expected:
            calls.append({
                "name": "write",
                "args": {
                    "path": "output/schema.json",
                    "content": json.dumps(expected["correct_schema"], indent=2),
                },
            })

        # Generic: if expected has an "output_files" key mapping path -> content
        if "output_files" in expected:
            for path, content in expected["output_files"].items():
                if isinstance(content, str):
                    calls.append({"name": "write", "args": {"path": path, "content": content}})
                else:
                    calls.append({
                        "name": "write",
                        "args": {"path": path, "content": json.dumps(content, indent=2)},
                    })

        return calls

    def _extract_task_id(self, messages: list[dict]) -> str:
        """Extract task_id from message content."""
        for msg in messages:
            content = msg.get("content", "")
            if "task:" in content.lower():
                # Find "task: XXXX" pattern
                for line in content.split("\n"):
                    if "task:" in line.lower():
                        parts = line.split(":")
                        if len(parts) >= 2:
                            return parts[-1].strip().split()[0].strip()
        return "unknown"

    def get_usage(self) -> dict:
        return dict(self._usage)
