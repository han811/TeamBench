"""
Parameterized generator for GH433_zap_1508.

Source PR:    https://github.com/uber-go/zap/pull/1508
Source Issue: N/A

Seed varies: renames 'action' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH433_zap_1508'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH433_zap_1508'
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
            task_id='GH433_zap_1508',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'uber-go/zap',
                "pr_number": 1508,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/uber-go/zap/pull/1508",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            '.github/workflows/go.yml': 'name: Go\n\non:\n  push:\n    branches: [master]\n    tags: [\'v*\']\n  pull_request:\n    branches: [\'*\']\n\npermissions:\n  contents: read\n\njobs:\n\n  build:\n    runs-on: ubuntu-latest\n    strategy:\n      matrix:\n        go: ["1.22.x", "1.23.x"]\n        include:\n        - go: 1.23.x\n\n    steps:\n    - name: Checkout code\n      uses: actions/checkout@v4\n\n    - name: Setup Go\n      uses: actions/setup-go@v5\n      with:\n        go-version: ${{ matrix.go }}\n        cache-dependency-path: \'**/go.sum\'\n\n    - name: Download Dependencies\n      run: |\n        go mod download\n        (cd tools && go mod download)\n        (cd benchmarks && go mod download)\n        (cd zapgrpc/internal/test && go mod download)\n\n    - name: Test\n      run: make cover\n\n    - name: Upload coverage to codecov.io\n      uses: codecov/codecov-action@v5\n      with:\n        verbose: true\n        token: ${{ secrets.CODECOV_TOKEN }}\n\n  lint:\n    name: Lint\n    runs-on: ubuntu-latest\n\n    steps:\n    - uses: actions/checkout@v4\n      name: Check out repository\n    - uses: actions/setup-go@v5\n      name: Set up Go\n      with:\n        go-version: 1.23.x\n        cache: false  # managed by golangci-lint\n\n    - uses: golangci/golangci-lint-action@v6\n      name: Install golangci-lint\n      with:\n        version: latest\n        # Hack: Use the official action to download, but not run.\n        # make lint below will handle actually running the linter.\n        args: --help\n\n    - run: make lint\n      name: Lint\n\n    - name: vulncheck\n      run: make vulncheck\n',
            'tools/go.mod': 'module go.uber.org/zap/tools\n\nrequire golang.org/x/vuln v1.1.3\n\nrequire (\n\tgolang.org/x/mod v0.19.0 // indirect\n\tgolang.org/x/sync v0.7.0 // indirect\n\tgolang.org/x/sys v0.22.0 // indirect\n\tgolang.org/x/telemetry v0.0.0-20240522233618-39ace7a40ae7 // indirect\n\tgolang.org/x/tools v0.23.0 // indirect\n)\n\ngo 1.21\n\ntoolchain go1.22.2\n',
            'tools/go.sum': 'github.com/google/go-cmdtest v0.4.1-0.20220921163831-55ab3332a786 h1:rcv+Ippz6RAtvaGgKxc+8FQIpxHgsF+HBzPyYL2cyVU=\ngithub.com/google/go-cmdtest v0.4.1-0.20220921163831-55ab3332a786/go.mod h1:apVn/GCasLZUVpAJ6oWAuyP7Ne7CEsQbTnc0plM3m+o=\ngithub.com/google/go-cmp v0.6.0 h1:ofyhxvXcZhMsU5ulbFiLKl/XBFqE1GSq7atu8tAmTRI=\ngithub.com/google/go-cmp v0.6.0/go.mod h1:17dUlkBOakJ0+DkrSSNjCkIjxS6bF9zb3elmeNGIjoY=\ngithub.com/google/renameio v0.1.0 h1:GOZbcHa3HfsPKPlmyPyN2KEohoMXOhdMbHrvbpl2QaA=\ngithub.com/google/renameio v0.1.0/go.mod h1:KWCgfxg9yswjAJkECMjeO8J8rahYeXnNhOm40UhjYkI=\ngolang.org/x/mod v0.19.0 h1:fEdghXQSo20giMthA7cd28ZC+jts4amQ3YMXiP5oMQ8=\ngolang.org/x/mod v0.19.0/go.mod h1:hTbmBsO62+eylJbnUtE2MGJUyE7QWk4xUqPFrRgJ+7c=\ngolang.org/x/sync v0.7.0 h1:YsImfSBoP9QPYL0xyKJPq0gcaJdG3rInoqxTWbfQu9M=\ngolang.org/x/sync v0.7.0/go.mod h1:Czt+wKu1gCyEFDUtn0jG5QVvpJ6rzVqr5aXyt9drQfk=\ngolang.org/x/sys v0.22.0 h1:RI27ohtqKCnwULzJLqkv897zojh5/DwS/ENaMzUOaWI=\ngolang.org/x/sys v0.22.0/go.mod h1:/VUhepiaJMQUp4+oa/7Zr1D23ma6VTLIYjOOTFZPUcA=\ngolang.org/x/telemetry v0.0.0-20240522233618-39ace7a40ae7 h1:FemxDzfMUcK2f3YY4H+05K9CDzbSVr2+q/JKN45pey0=\ngolang.org/x/telemetry v0.0.0-20240522233618-39ace7a40ae7/go.mod h1:pRgIJT+bRLFKnoM1ldnzKoxTIn14Yxz928LQRYYgIN0=\ngolang.org/x/tools v0.23.0 h1:SGsXPZ+2l4JsgaCKkx+FQ9YZ5XEtA1GZYuoDjenLjvg=\ngolang.org/x/tools v0.23.0/go.mod h1:pnu6ufv6vQkll6szChhK3C3L/ruaIv5eBeztNG8wtsI=\ngolang.org/x/vuln v1.1.3 h1:NPGnvPOTgnjBc9HTaUx+nj+EaUYxl5SJOWqaDYGaFYw=\ngolang.org/x/vuln v1.1.3/go.mod h1:7Le6Fadm5FOqE9C926BCD0g12NWyhg7cxV4BwcPFuNY=\n',
        }
