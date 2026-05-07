"""
Parameterized generator for GH620_urllib3_3727.

Source PR:    https://github.com/urllib3/urllib3/pull/3727
Source Issue: N/A

Seed varies: renames 'agent' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH620_urllib3_3727'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH620_urllib3_3727'
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
                files[fpath] = files[fpath].replace('agent', 'agent' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH620_urllib3_3727',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'urllib3/urllib3',
                "pr_number": 3727,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/urllib3/urllib3/pull/3727",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'README.md': '<h1 align="center">\n\n![urllib3](https://github.com/urllib3/urllib3/raw/main/docs/_static/banner_github.svg)\n\n</h1>\n\n<p align="center">\n  <a href="https://pypi.org/project/urllib3"><img alt="PyPI Version" src="https://img.shields.io/pypi/v/urllib3.svg?maxAge=86400" /></a>\n  <a href="https://pypi.org/project/urllib3"><img alt="Python Versions" src="https://img.shields.io/pypi/pyversions/urllib3.svg?maxAge=86400" /></a>\n  <a href="https://discord.gg/urllib3"><img alt="Join our Discord" src="https://img.shields.io/discord/756342717725933608?color=%237289da&label=discord" /></a>\n  <a href="https://github.com/urllib3/urllib3/actions?query=workflow%3ACI"><img alt="Coverage Status" src="https://img.shields.io/badge/coverage-100%25-success" /></a>\n  <a href="https://github.com/urllib3/urllib3/actions/workflows/ci.yml?query=branch%3Amain"><img alt="Build Status on GitHub" src="https://github.com/urllib3/urllib3/actions/workflows/ci.yml/badge.svg?branch:main&workflow:CI" /></a>\n  <a href="https://urllib3.readthedocs.io"><img alt="Documentation Status" src="https://readthedocs.org/projects/urllib3/badge/?version=latest" /></a><br>\n  <a href="https://deps.dev/pypi/urllib3"><img alt="OpenSSF Scorecard" src="https://api.securityscorecards.dev/projects/github.com/urllib3/urllib3/badge" /></a>\n  <a href="https://slsa.dev"><img alt="SLSA 3" src="https://slsa.dev/images/gh-badge-level3.svg" /></a>\n  <a href="https://bestpractices.coreinfrastructure.org/projects/6227"><img alt="CII Best Practices" src="https://bestpractices.coreinfrastructure.org/projects/6227/badge" /></a>\n</p>\n\nurllib3 is a powerful, *user-friendly* HTTP client for Python. Much of the\nPython ecosystem already uses urllib3 and you should too.\nurllib3 brings many critical features that are missing from the Python\nstandard libraries:\n\n- Thread safety.\n- Connection pooling.\n- Client-side SSL/TLS verification.\n- File uploads with multipart encoding.\n- Helpers for retrying requests and dealing with HTTP redirects.\n- Support for gzip, deflate, brotli, and zstd encoding.\n- Proxy support for HTTP and SOCKS.\n- 100% test coverage.\n\nurllib3 is powerful and easy to use:\n\n```python3\n>>> import urllib3\n>>> resp = urllib3.request("GET", "http://httpbin.org/robots.txt")\n>>> resp.status\n200\n>>> resp.data\nb"User-agent: *\\nDisallow: /deny\\n"\n```\n\n## Installing\n\nurllib3 can be installed with [pip](https://pip.pypa.io):\n\n```bash\n$ python -m pip install urllib3\n```\n\nAlternatively, you can grab the latest source code from [GitHub](https://github.com/urllib3/urllib3):\n\n```bash\n$ git clone https://github.com/urllib3/urllib3.git\n$ cd urllib3\n$ pip install .\n```\n\n\n## Documentation\n\nurllib3 has usage and reference documentation at [urllib3.readthedocs.io](https://urllib3.readthedocs.io).\n\n\n## Community\n\nurllib3 has a [community Discord channel](https://discord.gg/urllib3) for asking questions and\ncollaborating with other contributors. Drop by and say hello 👋\n\n\n## Contributing\n\nurllib3 happily accepts contributions. Please see our\n[contributing documentation](https://urllib3.readthedocs.io/en/latest/contributing.html)\nfor some tips on getting started.\n\n\n## Security Disclosures\n\nTo report a security vulnerability, please use the\n[Tidelift security contact](https://tidelift.com/security).\nTidelift will coordinate the fix and disclosure with maintainers.\n\n\n## Maintainers\n\n- Lead: [@illia-v](https://github.com/illia-v) (Illia Volochii)\n- [@sethmlarson](https://github.com/sethmlarson) (Seth M. Larson)\n- [@pquentin](https://github.com/pquentin) (Quentin Pradet)\n- [@theacodes](https://github.com/theacodes) (Thea Flowers)\n- [@haikuginger](https://github.com/haikuginger) (Jess Shapiro)\n- [@lukasa](https://github.com/lukasa) (Cory Benfield)\n- [@sigmavirus24](https://github.com/sigmavirus24) (Ian Stapleton Cordasco)\n- [@shazow](https://github.com/shazow) (Andrey Petrov)\n\n👋\n\n\n## Sponsorship\n\nIf your company benefits from this library, please consider [sponsoring its\ndevelopment](https://urllib3.readthedocs.io/en/latest/sponsors.html).\n\n\n## For Enterprise\n\nProfessional support for urllib3 is available as part of the [Tidelift\nSubscription][1].  Tidelift gives software development teams a single source for\npurchasing and maintaining their software, with professional grade assurances\nfrom the experts who know it best, while seamlessly integrating with existing\ntools.\n\n[1]: https://tidelift.com/subscription/pkg/pypi-urllib3?utm_source=pypi-urllib3&utm_medium=referral&utm_campaign=readme\n',
        }
