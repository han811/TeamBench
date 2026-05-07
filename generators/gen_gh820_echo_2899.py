"""
Parameterized generator for GH820_echo_2899.

Source PR:    https://github.com/labstack/echo/pull/2899
Source Issue: N/A

Seed varies: renames 'about' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH820_echo_2899'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH820_echo_2899'
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
                files[fpath] = files[fpath].replace('about', 'about' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH820_echo_2899',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'labstack/echo',
                "pr_number": 2899,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/labstack/echo/pull/2899",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            '.github/workflows/checks.yml': 'name: Run checks\n\non:\n  push:\n    branches:\n      - master\n  pull_request:\n    branches:\n      - master\n  workflow_dispatch:\n\npermissions:\n  contents: read #  to fetch code (actions/checkout)\n\nenv:\n  # run static analysis only with the latest Go version\n  LATEST_GO_VERSION: "1.25"\n\njobs:\n  check:\n    runs-on: ubuntu-latest\n    steps:\n      - name: Checkout Code\n        uses: actions/checkout@v5\n\n      - name: Set up Go ${{ matrix.go }}\n        uses: actions/setup-go@v5\n        with:\n          go-version: ${{ env.LATEST_GO_VERSION }}\n          check-latest: true\n\n      - name: Run golint\n        run: |\n          go install golang.org/x/lint/golint@latest\n          golint -set_exit_status ./...\n\n      - name: Run staticcheck\n        run: |\n          go install honnef.co/go/tools/cmd/staticcheck@latest\n          staticcheck ./...\n\n      - name: Run govulncheck\n        run: |\n          go version\n          go install golang.org/x/vuln/cmd/govulncheck@latest\n          govulncheck ./...\n\n',
            '.github/workflows/echo.yml': 'name: Run Tests\n\non:\n  push:\n    branches:\n      - master\n  pull_request:\n    branches:\n      - master\n  workflow_dispatch:\n\npermissions:\n  contents: read #  to fetch code (actions/checkout)\n\nenv:\n  # run coverage and benchmarks only with the latest Go version\n  LATEST_GO_VERSION: "1.25"\n\njobs:\n  test:\n    strategy:\n      matrix:\n        os: [ubuntu-latest, macos-latest, windows-latest]\n        # Each major Go release is supported until there are two newer major releases. https://golang.org/doc/devel/release.html#policy\n        # Echo tests with last four major releases (unless there are pressing vulnerabilities)\n        # As we depend on `golang.org/x/` libraries which only support the last 2 Go releases, we could have situations when\n        # we derive from the last four major releases promise.\n        go: ["1.25"]\n    name: ${{ matrix.os }} @ Go ${{ matrix.go }}\n    runs-on: ${{ matrix.os }}\n    steps:\n      - name: Checkout Code\n        uses: actions/checkout@v5\n\n      - name: Set up Go ${{ matrix.go }}\n        uses: actions/setup-go@v5\n        with:\n          go-version: ${{ matrix.go }}\n\n      - name: Run Tests\n        run: go test -race --coverprofile=coverage.coverprofile --covermode=atomic ./...\n\n      - name: Upload coverage to Codecov\n        if: success() && matrix.go == env.LATEST_GO_VERSION && matrix.os == \'ubuntu-latest\'\n        uses: codecov/codecov-action@v5\n        with:\n          token:\n          fail_ci_if_error: false\n\n  benchmark:\n    needs: test\n    name: Benchmark comparison\n    runs-on: ubuntu-latest\n    steps:\n      - name: Checkout Code (Previous)\n        uses: actions/checkout@v5\n        with:\n          ref: ${{ github.base_ref }}\n          path: previous\n\n      - name: Checkout Code (New)\n        uses: actions/checkout@v5\n        with:\n          path: new\n\n      - name: Set up Go ${{ matrix.go }}\n        uses: actions/setup-go@v5\n        with:\n          go-version: ${{ env.LATEST_GO_VERSION }}\n\n      - name: Install Dependencies\n        run: go install golang.org/x/perf/cmd/benchstat@latest\n\n      - name: Run Benchmark (Previous)\n        run: |\n          cd previous\n          go test -run="-" -bench=".*" -count=8 ./... > benchmark.txt\n\n      - name: Run Benchmark (New)\n        run: |\n          cd new\n          go test -run="-" -bench=".*" -count=8 ./... > benchmark.txt\n\n      - name: Run Benchstat\n        run: |\n          benchstat previous/benchmark.txt new/benchmark.txt\n',
            'SECURITY.md': '# Security Policy\n\n## Supported Versions\n\nUse this section to tell people about which versions of your project are\ncurrently being supported with security updates.\n\n| Version | Supported          |\n| ------- | ------------------ |\n| 5.x.x   | :white_check_mark:               |\n| > 4.15.x   | :white_check_mark: |\n| < 4.0   | :x:                |\n\n## Reporting a Vulnerability\n\nAt the moment look for maintainers email(s) in commits and email them.\n',
        }
