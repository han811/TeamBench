"""
Parameterized generator for GH560_poetry_10731.

Source PR:    https://github.com/python-poetry/poetry/pull/10731
Source Issue: N/A

Seed varies: renames 'authors' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH560_poetry_10731'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH560_poetry_10731'
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
                files[fpath] = files[fpath].replace('authors', 'authors' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH560_poetry_10731',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'python-poetry/poetry',
                "pr_number": 10731,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/python-poetry/poetry/pull/10731",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'README.md': '# Poetry: Python packaging and dependency management made easy\n\n[![Poetry](https://img.shields.io/endpoint?url=https://python-poetry.org/badge/v0.json)](https://python-poetry.org/)\n[![Stable Version](https://img.shields.io/pypi/v/poetry?label=stable)][PyPI Releases]\n[![Pre-release Version](https://img.shields.io/github/v/release/python-poetry/poetry?label=pre-release&include_prereleases&sort=semver)][PyPI Releases]\n[![Python Versions](https://img.shields.io/pypi/pyversions/poetry)][PyPI]\n[![Download Stats](https://img.shields.io/pypi/dm/poetry)](https://pypistats.org/packages/poetry)\n[![Discord](https://img.shields.io/discord/487711540787675139?logo=discord)][Discord]\n\nPoetry helps you declare, manage and install dependencies of Python projects,\nensuring you have the right stack everywhere.\n\n![Poetry Install](https://raw.githubusercontent.com/python-poetry/poetry/main/assets/install.gif)\n\nPoetry replaces `setup.py`, `requirements.txt`, `setup.cfg`, `MANIFEST.in` and `Pipfile` with a simple `pyproject.toml`\nbased project format.\n\n```toml\n[project]\nname = "my-package"\nversion = "0.1.0"\ndescription = "The description of the package"\n\nlicense = { text = "MIT" }\nreadme = "README.md"\n\n# No python upper bound for package metadata\nrequires-python = ">=3.9"\n\nauthors = [\n    { name = "Sébastien Eustace", email = "sebastien@eustace.io" },\n]\n\n# Keywords (translated to tags on the package index)\nkeywords = ["packaging", "poetry"]\n\ndependencies = [\n    # equivalent to ^3.8.1 with semver constraints\n    "aiohttp (>=3.8.1,<4.0.0)",\n    # dependency with extras\n    "requests[security] (>=2.28,<3.0)",\n    # version-specific dependency with prereleases allowed (see below)\n    "tomli (>=2.0.1,<3.0.0) ; python_version < \'3.11\'",\n    # git dependency with branch specified\n    "cleo @ git+https://github.com/python-poetry/cleo.git@main",\n]\n\n[project.urls]\nrepository = "https://github.com/python-poetry/poetry"\nhomepage = "https://python-poetry.org"\n\n# Scripts are easily expressed\n[project.scripts]\nmy_package_cli = \'my_package.console:run\'\n\n[project.optional-dependencies]\n# optional dependency to be installed via \'poetry install -E my-extra\'\nmy-extra = ["pendulum (>=3.1.0,<4.0.0)"]\n\n[tool.poetry.dependencies]\n# Python upper bound for locking\npython = ">=3.9,<4.0"\n# Version-specific dependencies with prereleases allowed\ntomli = { allow-prereleases = true }\n\n# Dependency groups are supported for organizing your dependencies\n[dependency-groups]\ndev = ["pytest (>=7.1.2,<8.0.0)", "pytest-cov (>=3.0,<4.0)"]\ndocs = ["Sphinx (>=5.1.1,<6.0.0)"]\n\n# ...and can be installed only when explicitly requested\n# via \'poetry install --with docs\'\n[tool.poetry.group.docs]\noptional = true\n\n# Alternatively, you can use Poetry specific syntax\n# to specify dependency groups\n[tool.poetry.group.lint]\noptional = true\n\n[tool.poetry.group.lint.dependencies]\nruff = ">=0.10.0"\n```\n\n## Installation\n\nPoetry supports multiple installation methods, including a simple script found at [install.python-poetry.org]. For full\ninstallation instructions, including advanced usage of the script, alternate install methods, and CI best practices, see\nthe full [installation documentation].\n\n## Documentation\n\n[Documentation] for the current version of Poetry (as well as the development branch and recently out of support\nversions) is available from the [official website].\n\n## Contribute\n\nPoetry is a large, complex project always in need of contributors. For those new to the project, a list of\n[suggested issues] to work on in Poetry and poetry-core is available. The full [contributing documentation] also\nprovides helpful guidance.\n\n## Resources\n\n* [Releases][PyPI Releases]\n* [Official Website]\n* [Documentation]\n* [Issue Tracker]\n* [Discord]\n\n  [PyPI]: https://pypi.org/project/poetry/\n  [PyPI Releases]: https://pypi.org/project/poetry/#history\n  [Official Website]: https://python-poetry.org\n  [Documentation]: https://python-poetry.org/docs/\n  [Issue Tracker]: https://github.com/python-poetry/poetry/issues\n  [Suggested Issues]: https://github.com/python-poetry/poetry/contribute\n  [Contributing Documentation]: https://python-poetry.org/docs/contributing\n  [Discord]: https://discord.com/invite/awxPgve\n  [install.python-poetry.org]: https://install.python-poetry.org\n  [Installation Documentation]: https://python-poetry.org/docs/#installation\n\n## Related Projects\n\n* [poetry-core](https://github.com/python-poetry/poetry-core): PEP 517 build-system for Poetry projects, and\ndependency-free core functionality of the Poetry frontend\n* [poetry-plugin-export](https://github.com/python-poetry/poetry-plugin-export): Export Poetry projects/lock files to\nforeign formats like requirements.txt\n* [poetry-plugin-bundle](https://github.com/python-poetry/poetry-plugin-bundle): Install Poetry projects/lock files to\nexternal formats like virtual environments\n* [install.python-poetry.org](https://github.com/python-poetry/install.python-poetry.org): The official Poetry\ninstallation script\n* [website](https://github.com/python-poetry/website): The official Poetry website and blog\n\n## Supporters\n\nThanks to [JetBrains](https://www.jetbrains.com) for supporting us with licenses for their tools.\n\n[<img src="https://resources.jetbrains.com/storage/products/company/brand/logos/jetbrains.svg" width="150" alt="JetBrains logo." />](https://www.jetbrains.com)\n',
        }
