"""
Parameterized generator for GH567_poetry_10766.

Source PR:    https://github.com/python-poetry/poetry/pull/10766
Source Issue: N/A

Seed varies: renames 'boom' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH567_poetry_10766'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH567_poetry_10766'
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
                files[fpath] = files[fpath].replace('boom', 'boom' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH567_poetry_10766',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'python-poetry/poetry',
                "pr_number": 10766,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/python-poetry/poetry/pull/10766",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'tests/test_helpers.py': 'from __future__ import annotations\n\nimport os\n\nfrom tests.helpers import flatten_dict\nfrom tests.helpers import isolated_environment\n\n\ndef test_flatten_dict() -> None:\n    orig_dict = {\n        "a": 1,\n        "b": 2,\n        "c": {\n            "x": 8,\n            "y": 9,\n        },\n    }\n\n    flattened_dict = {\n        "a": 1,\n        "b": 2,\n        "c:x": 8,\n        "c:y": 9,\n    }\n\n    assert flattened_dict == flatten_dict(orig_dict, delimiter=":")\n\n\ndef test_isolated_environment_restores_original_environ() -> None:\n    original_environ = dict(os.environ)\n    with isolated_environment():\n        os.environ["TEST_VAR"] = "test"\n    assert os.environ == original_environ\n\n\ndef test_isolated_environment_clears_environ() -> None:\n    os.environ["TEST_VAR"] = "test"\n    with isolated_environment(clear=True):\n        assert "TEST_VAR" not in os.environ\n    assert "TEST_VAR" in os.environ\n\n\ndef test_isolated_environment_updates_environ() -> None:\n    with isolated_environment(environ={"NEW_VAR": "new_value"}):\n        assert os.environ["NEW_VAR"] == "new_value"\n    assert "NEW_VAR" not in os.environ\n',
        }
