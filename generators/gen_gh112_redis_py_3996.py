"""
Parameterized generator for GH112_redis-py_3996.

Source PR:    https://github.com/redis/redis-py/pull/3996
Source Issue: https://github.com/redis/redis-py/issues/3992

Seed varies: renames 'accessible' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH112_redis-py_3996'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH112_redis-py_3996'
        )
        with open(os.path.join(tasks_dir, "spec.md")) as f:
            spec_md = f.read()
        with open(os.path.join(tasks_dir, "brief.md")) as f:
            brief_md = f.read()

        files = self._base_workspace()
        # Apply seed-based renaming to prevent direct memorization
        suffixes = ["", "_alt", "_impl"]
        suffix = suffixes[seed % len(suffixes)]
        if suffix:
            for fpath in list(files.keys()):
                files[fpath] = files[fpath].replace('accessible', 'accessible' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH112_redis-py_3996',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'redis/redis-py',
                "pr_number": 3996,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/redis/redis-py/pull/3996",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'redis/observability/__init__.py': '',
            'tests/test_observability/test_public_api.py': '"""\nUnit tests for redis.observability public API exports.\n\nThese tests verify that all symbols exported from redis.observability\nare correctly re-exported and match the original implementations.\n"""\n\n\nclass TestPublicAPIExports:\n    """Tests for public API exports from redis.observability."""\n\n    def test_otel_config_reexport(self):\n        """Test that OTelConfig is correctly re-exported."""\n        from redis.observability import OTelConfig\n        from redis.observability.config import OTelConfig as OriginalOTelConfig\n\n        assert OTelConfig is OriginalOTelConfig\n\n    def test_metric_group_reexport(self):\n        """Test that MetricGroup is correctly re-exported."""\n        from redis.observability import MetricGroup\n        from redis.observability.config import MetricGroup as OriginalMetricGroup\n\n        assert MetricGroup is OriginalMetricGroup\n\n    def test_telemetry_option_reexport(self):\n        """Test that TelemetryOption is correctly re-exported."""\n        from redis.observability import TelemetryOption\n        from redis.observability.config import (\n            TelemetryOption as OriginalTelemetryOption,\n        )\n\n        assert TelemetryOption is OriginalTelemetryOption\n\n    def test_observability_instance_reexport(self):\n        """Test that ObservabilityInstance is correctly re-exported."""\n        from redis.observability import ObservabilityInstance\n        from redis.observability.providers import (\n            ObservabilityInstance as OriginalObservabilityInstance,\n        )\n\n        assert ObservabilityInstance is OriginalObservabilityInstance\n\n    def test_get_observability_instance_reexport(self):\n        """Test that get_observability_instance is correctly re-exported."""\n        from redis.observability import get_observability_instance\n        from redis.observability.providers import (\n            get_observability_instance as original_get_observability_instance,\n        )\n\n        assert get_observability_instance is original_get_observability_instance\n\n    def test_reset_observability_instance_reexport(self):\n        """Test that reset_observability_instance is correctly re-exported."""\n        from redis.observability import reset_observability_instance\n        from redis.observability.providers import (\n            reset_observability_instance as original_reset_observability_instance,\n        )\n\n        assert reset_observability_instance is original_reset_observability_instance\n\n    def test_all_exports_defined(self):\n        """Test that __all__ contains all expected exports."""\n        import redis.observability as obs\n\n        expected_exports = {\n            "OTelConfig",\n            "MetricGroup",\n            "TelemetryOption",\n            "ObservabilityInstance",\n            "get_observability_instance",\n            "reset_observability_instance",\n        }\n\n        assert set(obs.__all__) == expected_exports\n\n    def test_all_exports_are_accessible(self):\n        """Test that all items in __all__ are actually accessible."""\n        import redis.observability as obs\n\n        for name in obs.__all__:\n            assert hasattr(obs, name), f"{name} is in __all__ but not accessible"\n            assert getattr(obs, name) is not None, f"{name} is None"\n',
        }
