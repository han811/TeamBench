"""
Parameterized generator for GH593_dateutil_1337.

Source PR:    https://github.com/dateutil/dateutil/pull/1337
Source Issue: N/A

Seed varies: renames 'actions' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH593_dateutil_1337'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH593_dateutil_1337'
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
                files[fpath] = files[fpath].replace('actions', 'actions' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH593_dateutil_1337',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'dateutil/dateutil',
                "pr_number": 1337,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/dateutil/dateutil/pull/1337",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            '.github/workflows/publish.yml': '# This workflow is triggered three ways:\n#\n# 1. Manually triggering the workflow via the GitHub UI (Actions > Upload\n#    package) will upload to test.pypi.org without the need to create a tag.\n# 2. When a tag is created, the workflow will upload the package to\n#    test.pypi.org.\n# 3. When a GitHub Release is made, the workflow will upload the package to pypi.org.\n#\n# It is done this way until PyPI has draft reviews, to allow for a two-stage\n# upload with a chance for manual intervention before the final publication.\nname: Upload package\n\non:\n  release:\n    types: [created]\n  push:\n    tags:\n      - \'*\'\n  workflow_dispatch:\n\njobs:\n  deploy:\n    runs-on: ubuntu-latest\n    steps:\n    - uses: actions/checkout@v3\n    - name: Set up Python\n      uses: actions/setup-python@v3\n      with:\n        python-version: \'3.9\'\n    - name: Install dependencies\n      run: |\n        python -m pip install --upgrade pip\n        pip install -U tox\n    - name: Create tox environments\n      run: |\n        tox -p -e py,build,release --notest\n    - name: Run tests\n      run: |\n        tox -e py\n    - name: Build package\n      run: |\n        tox -e build\n    - name: Publish package\n      env:\n        TWINE_USERNAME: "__token__"\n      run: |\n        if [[ "$GITHUB_EVENT_NAME" == "push" || \\\n              "$GITHUB_EVENT_NAME" == "workflow_dispatch" ]]; then\n          export TWINE_REPOSITORY_URL="https://test.pypi.org/legacy/"\n          export TWINE_PASSWORD="${{ secrets.TEST_PYPI_UPLOAD_TOKEN }}"\n        elif [[ "$GITHUB_EVENT_NAME" == "release" ]]; then\n          export TWINE_REPOSITORY="pypi"\n          export TWINE_PASSWORD="${{ secrets.PYPI_UPLOAD_TOKEN }}"\n        else\n          echo "Unknown event name: ${GITHUB_EVENT_NAME}"\n          exit 1\n        fi\n        tox -e release\n',
            '.github/workflows/validate.yml': 'name: Validate\n\non:\n  push:\n    branches:\n      - master\n  pull_request:\n    branches:\n      - master\n\njobs:\n  test:\n    strategy:\n      matrix:\n        python-version: [\n          "2.7",\n          "3.5",\n          "3.6",\n          "3.7",\n          "3.8",\n          "3.9",\n          "3.10",\n          "3.11",\n          "pypy-2.7",\n          "pypy-3.8",\n        ]\n        os: [ubuntu-latest, windows-latest, macos-latest]\n        exclude:\n          - python-version: "2.7"\n            os: "ubuntu-latest"\n          - python-version: "2.7"\n            os: "windows-latest"\n          - python-version: "2.7"\n            os: "macos-latest"\n          - python-version: "3.5"\n            os: "ubuntu-latest"\n          - python-version: "3.6"\n            os: "ubuntu-latest"\n        include:\n          - python-version: "2.7"\n            os: "ubuntu-20.04"\n          - python-version: "3.5"\n            os: "ubuntu-20.04"\n          - python-version: "3.6"\n            os: "ubuntu-20.04"\n    runs-on: ${{ matrix.os }}\n    env:\n      TOXENV: py\n    steps:\n      - uses: actions/checkout@v3\n      - if: ${{ matrix.python-version == \'2.7\' }}\n        run: |\n          sudo apt-get install python-is-python2\n          curl -sSL https://bootstrap.pypa.io/pip/2.7/get-pip.py -o get-pip.py\n          python get-pip.py\n        name: Set up Python ${{ matrix.python-version }} on ${{ matrix.os }}\n      - if: ${{ matrix.python-version != \'2.7\' }}\n        name: Set up Python ${{ matrix.python-version }} on ${{ matrix.os }}\n        uses: actions/setup-python@v3\n        with:\n          python-version: ${{ matrix.python-version }}\n      - name: Install dependencies\n        run: python -m pip install -U tox six\n      - name: Install zic (Windows)\n        run: |\n          curl https://get.enterprisedb.com/postgresql/postgresql-9.5.21-2-windows-x64-binaries.zip --output $env:GITHUB_WORKSPACE\\postgresql9.5.21.zip\n          unzip -oq $env:GITHUB_WORKSPACE\\postgresql9.5.21.zip -d .postgresql\n        if: runner.os == \'Windows\'\n      - name: Run updatezinfo.py (Windows)\n        run: |\n          $env:Path += ";$env:GITHUB_WORKSPACE\\.postgresql\\pgsql\\bin"\n          ci_tools/retry.bat python updatezinfo.py\n        if: runner.os == \'Windows\'\n      - name: Run updatezinfo.py (Unix)\n        run: ./ci_tools/retry.sh python updatezinfo.py\n        if: runner.os != \'Windows\'\n      - name: Run tox\n        run: python -m tox\n      - name: Generate coverage.xml\n        run: python -m tox -e coverage\n      - name: Report coverage to Codecov\n        uses: codecov/codecov-action@v3\n        with:\n          file: ./.tox/coverage.xml\n          name: ${{ matrix.os }}:${{ matrix.python-version }}\n          fail_ci_if_error: true\n\n  other:\n    runs-on: "ubuntu-latest"\n    strategy:\n      matrix:\n        toxenv: ["docs", "tz", "precommit"]\n    env:\n      TOXENV: ${{ matrix.toxenv }}\n\n    steps:\n      - uses: actions/checkout@v3\n        with:\n          fetch-depth: 0\n      - name: ${{ matrix.toxenv }}\n        uses: actions/setup-python@v4\n        with:\n          python-version: "3.10"\n      - name: Install tox\n        run: |\n          python -m pip install --upgrade pip\n          python -m pip install -U tox\n      - name: Run action\n        run: tox\n\n  darker:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v3\n        with:\n          fetch-depth: 0\n      - uses: actions/setup-python@v4\n      - uses: akaihola/darker@0fb2501a3f6c1b2d64976afa57885aeec0601182\n        # pinned due to unreleased fix: https://github.com/akaihola/darker/issues/489\n        with:\n          options: "--check --diff --color --isort"\n          src: "."\n          version: "~=1.7.1"\n\n  build-dist:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v3\n      - name: Set up Python\n        uses: actions/setup-python@v3\n        with:\n          python-version: "3.10"\n      - name: Install tox\n        run: python -m pip install -U tox\n      - name: Run tox\n        run: python -m tox -e build\n      - name: Check generation\n        run: |\n          exactly_one() {\n            value=$(find dist -iname $1 | wc -l)\n            if [ $value -ne 1 ]; then\n              echo "Found $value instances of $1, not 1"\n              return 1\n            else\n              echo "Found exactly 1 instance of $value"\n            fi\n          }\n          # Check that exactly one tarball and one wheel are created\n          exactly_one \'*.tar.gz\'\n          exactly_one \'*.whl\'\n',
        }
