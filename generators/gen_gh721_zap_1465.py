"""
Parameterized generator for GH721_zap_1465.

Source PR:    https://github.com/uber-go/zap/pull/1465
Source Issue: N/A

Seed varies: renames 'adheres' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH721_zap_1465'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH721_zap_1465'
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
                files[fpath] = files[fpath].replace('adheres', 'adheres' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH721_zap_1465',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'uber-go/zap',
                "pr_number": 1465,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/uber-go/zap/pull/1465",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'exp/CHANGELOG.md': "# Changelog\nAll notable changes to this project will be documented in this file.\n\nThis project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).\n\n## 0.2.0 - 9 Sep 2023\n\nBreaking changes:\n* [#1315][]: zapslog: Drop HandlerOptions.New in favor of just the NewHandler constructor.\n* [#1320][], [#1338][]: zapslog: Drop support for golang.org/x/exp/slog in favor of log/slog released in Go 1.21.\n\n[#1315]: https://github.com/uber-go/zap/pull/1315\n[#1320]: https://github.com/uber-go/zap/pull/1320\n[#1338]: https://github.com/uber-go/zap/pull/1338\n\n## 0.1.0 - 1 Aug 2023\n\nInitial release of go.uber.org/zap/exp.\nThis submodule contains experimental features for Zap.\nFeatures incubated here may be promoted to the root Zap module,\nbut it's not guaranteed.\n",
        }
