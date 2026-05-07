"""
Parameterized generator for GH503_click_3266.

Source PR:    https://github.com/pallets/click/pull/3266
Source Issue: N/A

Seed varies: renames 'action' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH503_click_3266'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH503_click_3266'
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
            task_id='GH503_click_3266',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'pallets/click',
                "pr_number": 3266,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/pallets/click/pull/3266",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            '.github/workflows/lock.yaml': "name: Lock inactive closed issues\n# Lock closed issues that have not received any further activity for two weeks.\n# This does not close open issues, only humans may do that. It is easier to\n# respond to new issues with fresh examples rather than continuing discussions\n# on old issues.\n\non:\n  schedule:\n    - cron: '0 0 * * *'\npermissions:\n  issues: write\n  pull-requests: write\n  discussions: write\nconcurrency:\n  group: lock\njobs:\n  lock:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: dessant/lock-threads@1bf7ec25051fe7c00bdd17e6a7cf3d7bfb7dc771 # v5.0.1\n        with:\n          issue-inactive-days: 14\n          pr-inactive-days: 14\n          discussion-inactive-days: 14\n",
            '.github/workflows/pre-commit.yaml': "name: pre-commit\non:\n  pull_request:\n  push:\n    branches: [main, stable]\njobs:\n  main:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@93cb6efe18208431cddfb8368fd83d5badbf9bfd # v5.0.1\n      - uses: astral-sh/setup-uv@5a7eac68fb9809dea845d802897dc5c723910fa3 # v7.1.3\n        with:\n          enable-cache: true\n          prune-cache: false\n      - uses: actions/setup-python@e797f83bcb11b83ae66e0230d6156d7c80228e7c # v6.0.0\n        id: setup-python\n        with:\n          python-version-file: pyproject.toml\n      - uses: actions/cache@0057852bfaa89a56745cba8c7296529d2fc39830 # v4.3.0\n        with:\n          path: ~/.cache/pre-commit\n          key: pre-commit|${{ hashFiles('pyproject.toml', '.pre-commit-config.yaml') }}\n      - run: uv run --locked --group pre-commit pre-commit run --show-diff-on-failure --color=always --all-files\n      - uses: pre-commit-ci/lite-action@5d6cc0eb514c891a40562a58a8e71576c5c7fb43 # v1.1.0\n        if: ${{ !cancelled() }}\n",
            '.github/workflows/publish.yaml': 'name: Publish\non:\n  push:\n    tags: [\'*\']\njobs:\n  build:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@93cb6efe18208431cddfb8368fd83d5badbf9bfd # v5.0.1\n      - uses: astral-sh/setup-uv@5a7eac68fb9809dea845d802897dc5c723910fa3 # v7.1.3\n        with:\n          enable-cache: true\n          prune-cache: false\n      - uses: actions/setup-python@e797f83bcb11b83ae66e0230d6156d7c80228e7c # v6.0.0\n        with:\n          python-version-file: pyproject.toml\n      - run: echo "SOURCE_DATE_EPOCH=$(git log -1 --pretty=%ct)" >> $GITHUB_ENV\n      - run: uv build\n      - uses: actions/upload-artifact@330a01c490aca151604b8cf639adc76d48f6c5d4 # v5.0.0\n        with:\n          path: ./dist\n  create-release:\n    needs: [build]\n    runs-on: ubuntu-latest\n    permissions:\n      contents: write\n    steps:\n      - uses: actions/download-artifact@018cc2cf5baa6db3ef3c5f8a56943fffe632ef53 # v6.0.0\n      - name: create release\n        run: gh release create --draft --repo ${{ github.repository }} ${{ github.ref_name }} artifact/*\n        env:\n          GH_TOKEN: ${{ github.token }}\n  publish-pypi:\n    needs: [build]\n    environment:\n      name: publish\n      url: https://pypi.org/project/click/${{ github.ref_name }}\n    runs-on: ubuntu-latest\n    permissions:\n      id-token: write\n    steps:\n      - uses: actions/download-artifact@018cc2cf5baa6db3ef3c5f8a56943fffe632ef53 # v6.0.0\n      - uses: pypa/gh-action-pypi-publish@ed0c53931b1dc9bd32cbe73a98c7f6766f8a527e # v1.13.0\n        with:\n          packages-dir: artifact/\n',
            '.github/workflows/test-flask.yaml': 'name: Test Flask Main\non:\n  pull_request:\n    paths-ignore: [\'docs/**\', \'README.md\']\n  push:\n    branches: [main, stable]\n    paths-ignore: [\'docs/**\', \'README.md\']\njobs:\n  flask-tests:\n    name: flask-tests\n    runs-on: ubuntu-latest\n    steps:\n      - uses: astral-sh/setup-uv@5a7eac68fb9809dea845d802897dc5c723910fa3 # v7.1.3\n        with:\n          enable-cache: true\n          prune-cache: false\n      - run: git clone https://github.com/pallets/flask\n      - run: uv venv --python 3.14\n        working-directory: ./flask\n      - run: source .venv/bin/activate\n        working-directory: ./flask\n      - run: uv sync --all-extras\n        working-directory: ./flask\n      - run: uv run --with "git+https://github.com/pallets/click.git@main" -- pytest\n        working-directory: ./flask\n',
            '.github/workflows/tests.yaml': "name: Tests\non:\n  pull_request:\n    paths-ignore: ['docs/**', 'README.md']\n  push:\n    branches: [main, stable]\n    paths-ignore: ['docs/**', 'README.md']\njobs:\n  tests:\n    name: ${{ matrix.name || matrix.python }}\n    runs-on: ${{ matrix.os || 'ubuntu-latest' }}\n    strategy:\n      fail-fast: false\n      matrix:\n        include:\n          - {python: '3.14'}\n          - {name: free-threaded-latest, python: '3.14t'}\n          - {python: '3.13'}\n          - {name: Windows, python: '3.13', os: windows-latest}\n          - {name: Mac, python: '3.13', os: macos-latest}\n          - {python: '3.12'}\n          - {python: '3.11'}\n          - {python: '3.10'}\n          - {name: PyPy, python: 'pypy-3.11', tox: pypy3.11}\n    steps:\n      - uses: actions/checkout@93cb6efe18208431cddfb8368fd83d5badbf9bfd # v5.0.1\n      - uses: astral-sh/setup-uv@5a7eac68fb9809dea845d802897dc5c723910fa3 # v7.1.3\n        with:\n          enable-cache: true\n          prune-cache: false\n      - uses: actions/setup-python@e797f83bcb11b83ae66e0230d6156d7c80228e7c # v6.0.0\n        with:\n          python-version: ${{ matrix.python }}\n      - run: uv run --locked tox run -e ${{ matrix.tox || format('py{0}', matrix.python) }}\n  stress:\n    name: stress (${{ matrix.name || matrix.python }})\n    runs-on: ${{ matrix.os || 'ubuntu-latest' }}\n    strategy:\n      fail-fast: false\n      matrix:\n        include:\n          - {python: '3.14'}\n          - {name: free-threaded, python: '3.14t', tox: stress-py3.14t}\n    steps:\n      - uses: actions/checkout@93cb6efe18208431cddfb8368fd83d5badbf9bfd # v5.0.1\n      - uses: astral-sh/setup-uv@5a7eac68fb9809dea845d802897dc5c723910fa3 # v7.1.3\n        with:\n          enable-cache: true\n          prune-cache: false\n      - uses: actions/setup-python@e797f83bcb11b83ae66e0230d6156d7c80228e7c # v6.0.0\n        with:\n          python-version: ${{ matrix.python }}\n      - run: uv run --locked tox run -e ${{ matrix.tox || format('stress-py{0}', matrix.python) }}\n  typing:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@93cb6efe18208431cddfb8368fd83d5badbf9bfd # v5.0.1\n      - uses: astral-sh/setup-uv@5a7eac68fb9809dea845d802897dc5c723910fa3 # v7.1.3\n        with:\n          enable-cache: true\n          prune-cache: false\n      - uses: actions/setup-python@e797f83bcb11b83ae66e0230d6156d7c80228e7c # v6.0.0\n        with:\n          python-version-file: pyproject.toml\n      - name: cache mypy\n        uses: actions/cache@0057852bfaa89a56745cba8c7296529d2fc39830 # v4.3.0\n        with:\n          path: ./.mypy_cache\n          key: mypy|${{ hashFiles('pyproject.toml') }}\n      - run: uv run --locked tox run -e typing\n",
            '.pre-commit-config.yaml': 'repos:\n  - repo: https://github.com/astral-sh/ruff-pre-commit\n    rev: 488940d9de1b658fac229e34c521d75a6ea476f2  # frozen: v0.14.5\n    hooks:\n      - id: ruff\n      - id: ruff-format\n  - repo: https://github.com/astral-sh/uv-pre-commit\n    rev: b6675a113e27a9b18f3d60c05794d62ca80c7ab5  # frozen: 0.9.9\n    hooks:\n      - id: uv-lock\n  - repo: https://github.com/pre-commit/pre-commit-hooks\n    rev: 3e8a8703264a2f4a69428a0aa4dcb512790b2c8c  # frozen: v6.0.0\n    hooks:\n      - id: check-merge-conflict\n      - id: debug-statements\n      - id: fix-byte-order-marker\n      - id: trailing-whitespace\n      - id: end-of-file-fixer\n',
        }
