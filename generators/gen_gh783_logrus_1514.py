"""
Parameterized generator for GH783_logrus_1514.

Source PR:    https://github.com/sirupsen/logrus/pull/1514
Source Issue: N/A

Seed varies: renames 'action' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH783_logrus_1514'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH783_logrus_1514'
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
            task_id='GH783_logrus_1514',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'sirupsen/logrus',
                "pr_number": 1514,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/sirupsen/logrus/pull/1514",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            '.github/workflows/ci.yaml': 'name: CI\n\non:\n  push:\n    branches:\n      - master\n  pull_request:\n    branches:\n      - master\n\nenv:\n  GOTOOLCHAIN: local\n\njobs:\n\n  lint:\n    name: Golang-CI Lint\n    timeout-minutes: 10\n    strategy:\n      matrix:\n        platform: [ubuntu-latest]\n    runs-on: ${{ matrix.platform }}\n    steps:\n      - name: Install Go\n        uses: actions/setup-go@v6\n        with:\n          go-version: stable\n      - uses: actions/checkout@v6\n      - uses: golangci/golangci-lint-action@v9\n  cross:\n    name: Cross\n    timeout-minutes: 10\n    runs-on: ubuntu-latest\n    steps:\n      - name: Checkout code\n        uses: actions/checkout@v6\n      - name: Install Go\n        uses: actions/setup-go@v6\n        with:\n          go-version: stable\n      - name: Build\n        run: |\n          for target in $(go tool dist list); do\n            echo "Building for $target"\n            GOOS=${target%/*} GOARCH=${target#*/} go build ./...\n          done\n\n  test:\n    name: Unit test\n    timeout-minutes: 10\n    strategy:\n      matrix:\n        go-version: [stable, oldstable, 1.23.x]\n        platform: [ubuntu-latest, windows-latest, macos-latest]\n    runs-on: ${{ matrix.platform }}\n    steps:\n    - name: Install Go\n      uses: actions/setup-go@v6\n      with:\n        go-version: ${{ matrix.go-version }}\n    - name: Checkout code\n      uses: actions/checkout@v6\n    - name: Test\n      run: go test -race -v ./...\n',
        }
