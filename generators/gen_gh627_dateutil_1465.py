"""
Parameterized generator for GH627_dateutil_1465.

Source PR:    https://github.com/dateutil/dateutil/pull/1465
Source Issue: N/A

Seed varies: renames 'action' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH627_dateutil_1465'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH627_dateutil_1465'
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
            task_id='GH627_dateutil_1465',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'dateutil/dateutil',
                "pr_number": 1465,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/dateutil/dateutil/pull/1465",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            '.github/workflows/validate.yml': 'name: Validate\n\non:\n  push:\n    branches:\n      - master\n  pull_request:\n    branches:\n      - master\n\nenv:\n  pypi-hosts: "pypi.python.org pypi.org files.pythonhosted.org"\n\njobs:\n  test:\n    strategy:\n      matrix:\n        python-version: [\n          "3.8",\n          "3.9",\n          "3.10",\n          "3.11",\n          "3.12",\n          "3.13",\n          "pypy-2.7",\n          "pypy-3.8",\n        ]\n        os: [ubuntu-latest, windows-latest, macos-latest]\n        include:\n          # Older versions (<=3.7) are included separately since they need\n          # special handling (using an older os or a container)\n          - os: "macos-13"\n            python-version: "3.5"\n          - os: "macos-13"\n            python-version: "3.6"\n          - os: "macos-13"\n            python-version: "3.7"\n          - os: "windows-latest"\n            python-version: "3.5"\n          - os: "windows-latest"\n            python-version: "3.6"\n          - os: "windows-latest"\n            python-version: "3.7"\n          - os: "ubuntu-latest"\n            python-version: "2.7"\n            use-container: true\n          - os: "ubuntu-latest"\n            python-version: "3.5"\n            use-container: true\n          - os: "ubuntu-latest"\n            python-version: "3.6"\n            use-container: true\n          - os: "ubuntu-latest"\n            python-version: "3.7"\n            use-container: true\n    runs-on: ${{ matrix.os }}\n    container:\n      image: ${{ matrix.use-container && format(\'python:{0}\', matrix.python-version) || \'\' }}\n    env:\n      TOXENV: py\n    steps:\n      - name: Checkout code\n        uses: actions/checkout@v4\n      - if: ${{ !matrix.use-container }}\n        name: Set up Python ${{ matrix.python-version }} on ${{ matrix.os }} (non-containers)\n        uses: actions/setup-python@v5\n        with:\n          python-version: ${{ matrix.python-version }}\n          allow-prereleases: true\n        env:\n          PIP_TRUSTED_HOST: ${{ contains(fromJson(\'["3.5"]\'), matrix.python-version) && env.pypi-hosts || \'\' }}\n      - name: Install dependencies\n        run: python -m pip install -U tox six\n      - name: Install zic (Windows)\n        run: |\n          curl https://get.enterprisedb.com/postgresql/postgresql-9.5.21-2-windows-x64-binaries.zip --output $env:GITHUB_WORKSPACE\\postgresql9.5.21.zip\n          unzip -oq $env:GITHUB_WORKSPACE\\postgresql9.5.21.zip -d .postgresql\n        if: runner.os == \'Windows\'\n      - name: Run updatezinfo.py (Windows)\n        run: |\n          $env:Path += ";$env:GITHUB_WORKSPACE\\.postgresql\\pgsql\\bin"\n          ci_tools/retry.bat python updatezinfo.py\n        if: runner.os == \'Windows\'\n      - name: Run updatezinfo.py (Unix)\n        run: ./ci_tools/retry.sh python updatezinfo.py\n        if: runner.os != \'Windows\'\n      - name: Run tox\n        run: python -m tox\n      - name: Generate coverage.xml\n        run: python -m tox -e coverage\n      - name: Report coverage to Codecov\n        uses: codecov/codecov-action@v3\n        with:\n          file: ./.tox/coverage.xml\n          name: ${{ matrix.os }}:${{ matrix.python-version }}\n          fail_ci_if_error: false\n          # codecov/codecov-action@v3 needs v0.7.3 to work on (intel) macos-13\n          # See https://github.com/codecov/codecov-action/issues/1549\n          version: ${{ matrix.os == \'macos-13\' && \'v0.7.3\' || \'latest\' }}\n\n  other:\n    runs-on: "ubuntu-latest"\n    strategy:\n      matrix:\n        toxenv: ["docs", "tz", "precommit"]\n    env:\n      TOXENV: ${{ matrix.toxenv }}\n\n    steps:\n      - uses: actions/checkout@v3\n        with:\n          fetch-depth: 0\n      - name: ${{ matrix.toxenv }}\n        uses: actions/setup-python@v5\n        with:\n          python-version: "3.10"\n      - name: Install tox\n        run: |\n          python -m pip install --upgrade pip\n          python -m pip install -U tox\n      - name: Run action\n        run: tox\n\n  darker:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v3\n        with:\n          fetch-depth: 0\n      - uses: actions/setup-python@v5\n      - uses: akaihola/darker@0fb2501a3f6c1b2d64976afa57885aeec0601182\n        # pinned due to unreleased fix: https://github.com/akaihola/darker/issues/489\n        with:\n          options: "--check --diff --color --isort"\n          src: "."\n          version: "~=1.7.1"\n\n  build-dist:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v3\n      - name: Set up Python\n        uses: actions/setup-python@v5\n        with:\n          python-version: "3.10"\n      - name: Install tox\n        run: python -m pip install -U tox\n      - name: Run tox\n        run: python -m tox -e build\n      - name: Check generation\n        run: |\n          exactly_one() {\n            value=$(find dist -iname $1 | wc -l)\n            if [ $value -ne 1 ]; then\n              echo "Found $value instances of $1, not 1"\n              return 1\n            else\n              echo "Found exactly 1 instance of $value"\n            fi\n          }\n          # Check that exactly one tarball and one wheel are created\n          exactly_one \'*.tar.gz\'\n          exactly_one \'*.whl\'\n',
        }
