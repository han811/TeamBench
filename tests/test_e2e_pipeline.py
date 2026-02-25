"""
End-to-end pipeline integration test using MockAdapter.

Verifies the full chain: Generator -> setup_run -> Orchestrator -> Grader
without any API keys. This is the strongest evidence that the benchmark
infrastructure works correctly.
"""
from __future__ import annotations

import json
import os
import tempfile

import pytest

from harness.adapters.mock_adapter import MockAdapter
from harness.run_all import setup_run, grade_run


# Test a representative subset of tasks (one per domain)
E2E_TASKS = [
    "P1_policy_config",   # policy: exact config match
    "IR2_misinformation_trap",  # IR: evidence-based answer
]


@pytest.fixture
def tmp_runs_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


class TestMockAdapterBasics:
    """Verify MockAdapter implements the interface correctly."""

    def test_adapter_creates(self):
        adapter = MockAdapter()
        assert adapter.model == "mock-adapter"

    def test_adapter_generates_response(self):
        adapter = MockAdapter()
        resp = adapter.generate_with_tools(
            messages=[{"role": "user", "content": "Hello"}],
            system_prompt="You are the Planner.",
            tools=[{"name": "read", "description": "Read file", "parameters": {}}],
        )
        assert resp.text
        assert isinstance(resp.tool_calls, list)

    def test_adapter_tracks_usage(self):
        adapter = MockAdapter()
        adapter.generate_with_tools(
            messages=[{"role": "user", "content": "test"}],
            system_prompt="You are the Planner.",
            tools=[],
        )
        usage = adapter.get_usage()
        assert usage["total_tokens"] > 0

    def test_adapter_factory(self):
        from harness.adapters import create_adapter
        adapter = create_adapter(model="mock-adapter")
        assert isinstance(adapter, MockAdapter)


class TestSetupRunIntegration:
    """Verify setup_run stages workspace correctly for parameterized tasks."""

    @pytest.mark.parametrize("task_name", E2E_TASKS)
    def test_setup_creates_workspace(self, task_name, tmp_runs_dir):
        run_id, run_dir, task_dir = setup_run(
            task_name, os.path.abspath("tasks"), tmp_runs_dir, seed=0
        )
        workspace = os.path.join(run_dir, "workspace")
        reports = os.path.join(run_dir, "reports")

        assert os.path.isdir(workspace), f"workspace not created for {task_name}"
        assert os.path.isdir(reports), f"reports not created for {task_name}"

        # expected.json should exist for parameterized tasks
        expected_path = os.path.join(reports, "expected.json")
        assert os.path.isfile(expected_path), f"expected.json not generated for {task_name}"

        with open(expected_path) as f:
            expected = json.load(f)
        assert isinstance(expected, dict)

    @pytest.mark.parametrize("task_name", E2E_TASKS)
    def test_different_seeds_produce_different_expected(self, task_name, tmp_runs_dir):
        """Parameterized tasks must produce different expected.json for different seeds."""
        _, run_dir_0, _ = setup_run(task_name, os.path.abspath("tasks"), tmp_runs_dir, seed=0)
        _, run_dir_1, _ = setup_run(task_name, os.path.abspath("tasks"), tmp_runs_dir, seed=1)

        exp_0 = json.loads(open(os.path.join(run_dir_0, "reports", "expected.json")).read())
        exp_1 = json.loads(open(os.path.join(run_dir_1, "reports", "expected.json")).read())

        assert exp_0 != exp_1, f"{task_name}: seeds 0 and 1 produced identical expected.json"


class TestGraderIntegration:
    """Verify graders work with generated expected.json."""

    @pytest.mark.parametrize("task_name", E2E_TASKS)
    def test_initial_state_fails(self, task_name, tmp_runs_dir):
        """Initial buggy workspace should fail grading."""
        _, run_dir, task_dir = setup_run(
            task_name, os.path.abspath("tasks"), tmp_runs_dir, seed=0
        )
        # Write stub attestation so grader proceeds
        submission = os.path.join(run_dir, "submission")
        os.makedirs(submission, exist_ok=True)
        att = {"task_id": task_name, "verdict": "pass", "checklist": []}
        with open(os.path.join(submission, "attestation.json"), "w") as f:
            json.dump(att, f)

        score = grade_run(task_name, task_dir, run_dir)
        assert not score.get("pass"), f"{task_name}: initial state should FAIL grading"
