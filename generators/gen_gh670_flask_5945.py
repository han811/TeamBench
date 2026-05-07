"""
Parameterized generator for GH670_flask_5945.

Source PR:    https://github.com/pallets/flask/pull/5945
Source Issue: N/A

Seed varies: renames 'action' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH670_flask_5945'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH670_flask_5945'
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
            task_id='GH670_flask_5945',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'pallets/flask',
                "pr_number": 5945,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/pallets/flask/pull/5945",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            '.github/workflows/lock.yaml': "name: Lock inactive closed issues\n# Lock closed issues that have not received any further activity for two weeks.\n# This does not close open issues, only humans may do that. It is easier to\n# respond to new issues with fresh examples rather than continuing discussions\n# on old issues.\n\non:\n  schedule:\n    - cron: '0 0 * * *'\npermissions:\n  issues: write\n  pull-requests: write\n  discussions: write\nconcurrency:\n  group: lock\njobs:\n  lock:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: dessant/lock-threads@7266a7ce5c1df01b1c6db85bf8cd86c737dadbe7 # v6.0.0\n        with:\n          issue-inactive-days: 14\n          pr-inactive-days: 14\n          discussion-inactive-days: 14\n",
            '.github/workflows/pre-commit.yaml': "name: pre-commit\non:\n  pull_request:\n  push:\n    branches: [main, stable]\njobs:\n  main:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd # v6.0.2\n      - uses: astral-sh/setup-uv@61cb8a9741eeb8a550a1b8544337180c0fc8476b # v7.2.0\n        with:\n          enable-cache: true\n          prune-cache: false\n      - uses: actions/setup-python@a309ff8b426b58ec0e2a45f0f869d46889d02405 # v6.2.0\n        id: setup-python\n        with:\n          python-version-file: pyproject.toml\n      - uses: actions/cache@8b402f58fbc84540c8b491a91e594a4576fec3d7 # v5.0.2\n        with:\n          path: ~/.cache/pre-commit\n          key: pre-commit|${{ hashFiles('pyproject.toml', '.pre-commit-config.yaml') }}\n      - run: uv run --locked --group pre-commit pre-commit run --show-diff-on-failure --color=always --all-files\n      - uses: pre-commit-ci/lite-action@5d6cc0eb514c891a40562a58a8e71576c5c7fb43 # v1.1.0\n        if: ${{ !cancelled() }}\n",
            '.github/workflows/publish.yaml': 'name: Publish\non:\n  push:\n    tags: [\'*\']\njobs:\n  build:\n    runs-on: ubuntu-latest\n    outputs:\n      artifact-id: ${{ steps.upload-artifact.outputs.artifact-id }}\n    steps:\n      - uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd # v6.0.2\n        with:\n          persist-credentials: false\n      - uses: astral-sh/setup-uv@61cb8a9741eeb8a550a1b8544337180c0fc8476b # v7.2.0\n        with:\n          enable-cache: true\n          prune-cache: false\n      - uses: actions/setup-python@a309ff8b426b58ec0e2a45f0f869d46889d02405 # v6.2.0\n        with:\n          python-version-file: pyproject.toml\n      - run: echo "SOURCE_DATE_EPOCH=$(git log -1 --pretty=%ct)" >> $GITHUB_ENV\n      - run: uv build\n      - uses: actions/upload-artifact@b7c566a772e6b6bfb58ed0dc250532a479d7789f # v6.0.0\n        id: upload-artifact\n        with:\n          name: dist\n          path: dist/\n          if-no-files-found: error\n  create-release:\n    needs: [build]\n    runs-on: ubuntu-latest\n    permissions:\n      contents: write\n    steps:\n      - uses: actions/download-artifact@37930b1c2abaa49bbe596cd826c3c89aef350131 # v7.0.0\n        with:\n          artifact-ids: ${{ needs.build.outputs.artifact-id }}\n          path: dist/\n      - name: create release\n        run: gh release create --draft --repo ${{ github.repository }} ${{ github.ref_name }} dist/*\n        env:\n          GH_TOKEN: ${{ github.token }}\n  publish-pypi:\n    needs: [build]\n    environment:\n      name: publish\n      url: https://pypi.org/project/Flask/${{ github.ref_name }}\n    runs-on: ubuntu-latest\n    permissions:\n      id-token: write\n    steps:\n      - uses: actions/download-artifact@37930b1c2abaa49bbe596cd826c3c89aef350131 # v7.0.0\n        with:\n          artifact-ids: ${{ needs.build.outputs.artifact-id }}\n          path: dist/\n      - uses: pypa/gh-action-pypi-publish@ed0c53931b1dc9bd32cbe73a98c7f6766f8a527e # v1.13.0\n        with:\n          packages-dir: "dist/"\n',
            '.github/workflows/tests.yaml': "name: Tests\non:\n  pull_request:\n    paths-ignore: ['docs/**', 'README.md']\n  push:\n    branches: [main, stable]\n    paths-ignore: ['docs/**', 'README.md']\njobs:\n  tests:\n    name: ${{ matrix.name || matrix.python }}\n    runs-on: ${{ matrix.os || 'ubuntu-latest' }}\n    strategy:\n      fail-fast: false\n      matrix:\n        include:\n          - {python: '3.14'}\n          - {python: '3.14t'}\n          - {name: Windows, python: '3.14', os: windows-latest}\n          - {name: Mac, python: '3.14', os: macos-latest}\n          - {python: '3.13'}\n          - {python: '3.12'}\n          - {python: '3.11'}\n          - {python: '3.10'}\n          - {python: '3.9'}\n          - {name: PyPy, python: 'pypy-3.11', tox: pypy3.11}\n          - {name: Minimum Versions, python: '3.14', tox: tests-min}\n          - {name: Development Versions, python: '3.10', tox: tests-dev}\n    steps:\n      - uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd # v6.0.2\n      - uses: astral-sh/setup-uv@61cb8a9741eeb8a550a1b8544337180c0fc8476b # v7.2.0\n        with:\n          enable-cache: true\n          prune-cache: false\n      - uses: actions/setup-python@a309ff8b426b58ec0e2a45f0f869d46889d02405 # v6.2.0\n        with:\n          python-version: ${{ matrix.python }}\n      - run: uv run --locked tox run -e ${{ matrix.tox || format('py{0}', matrix.python) }}\n  typing:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd # v6.0.2\n      - uses: astral-sh/setup-uv@61cb8a9741eeb8a550a1b8544337180c0fc8476b # v7.2.0\n        with:\n          enable-cache: true\n          prune-cache: false\n      - uses: actions/setup-python@a309ff8b426b58ec0e2a45f0f869d46889d02405 # v6.2.0\n        with:\n          python-version-file: pyproject.toml\n      - name: cache mypy\n        uses: actions/cache@8b402f58fbc84540c8b491a91e594a4576fec3d7 # v5.0.2\n        with:\n          path: ./.mypy_cache\n          key: mypy|${{ hashFiles('pyproject.toml') }}\n      - run: uv run --locked tox run -e typing\n",
        }
