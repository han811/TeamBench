"""
Parameterized generator for GH86_mux_734.

Source PR:    https://github.com/gorilla/mux/pull/734
Source Issue: https://github.com/gorilla/mux/issues/1234

Seed varies: renames 'action' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH86_mux_734'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH86_mux_734'
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
                files[fpath] = files[fpath].replace('action', 'action' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH86_mux_734',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'gorilla/mux',
                "pr_number": 734,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/gorilla/mux/pull/734",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            '.github/workflows/issues.yml': '# Add issues or pull-requests created to the project. \nname: Add issue or pull request to Project\n\non:\n  issues:\n    types:\n      - opened\n  pull_request_target:\n    types:\n      - opened\n      - reopened\n\njobs:\n  add-to-project:\n    runs-on: ubuntu-latest\n    steps:\n      - name: Add issue to project\n        uses: actions/add-to-project@v0.5.0\n        with:\n          project-url: https://github.com/orgs/gorilla/projects/4\n          github-token: ${{ secrets.ADD_TO_PROJECT_TOKEN }}\n',
            '.github/workflows/test.yml': "name: CI\non:\n  push:\n    branches:\n      - main\n  pull_request:\n    branches:\n      - main\n\npermissions:\n  contents: read\n\njobs:\n  verify-and-test:\n    strategy:\n      matrix:\n        go: ['1.19','1.20']\n        os: [ubuntu-latest, macos-latest, windows-latest]\n      fail-fast: true\n    runs-on: ${{ matrix.os }}\n    steps:\n      - name: Checkout Code\n        uses: actions/checkout@v3\n\n      - name: Setup Go ${{ matrix.go }}\n        uses: actions/setup-go@v4\n        with:\n          go-version: ${{ matrix.go }}\n          cache: false\n\n      - name: Run GolangCI-Lint\n        uses: golangci/golangci-lint-action@v3\n        with:\n          version: v1.53\n          args: --timeout=5m\n\n      - name: Run GoSec\n        if: matrix.os == 'ubuntu-latest'\n        uses: securego/gosec@master\n        with:\n          args: ./...\n\n      - name: Run GoVulnCheck\n        uses: golang/govulncheck-action@v1\n        with:\n          go-version-input: ${{ matrix.go }}\n          go-package: ./...\n\n      - name: Run Tests\n        run: go test -race -cover -coverprofile=coverage -covermode=atomic -v ./...\n\n      - name: Upload coverage to Codecov\n        uses: codecov/codecov-action@v3\n        with:\n          files: ./coverage",
            'go.mod': 'module github.com/gorilla/mux\n\ngo 1.19\n',
        }
