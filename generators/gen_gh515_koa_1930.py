"""
Parameterized generator for GH515_koa_1930.

Source PR:    https://github.com/koajs/koa/pull/1930
Source Issue: N/A

Seed varies: renames 'actions' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH515_koa_1930'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH515_koa_1930'
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
            task_id='GH515_koa_1930',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'koajs/koa',
                "pr_number": 1930,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/koajs/koa/pull/1930",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            '.github/workflows/npm-publish.yml': 'name: NPM Publish\n\n# Trigger only when tags matching semver format are pushed\n# Patterns match common semver formats:\n#   - v1.0.0 (standard)\n#   - v1.0.0-alpha (pre-release)\n#   - v1.0.0-beta.1 (pre-release with number)\n#\n# Note: GitHub Actions uses glob patterns (not full regex), which limits\n# complex semver matching. These patterns cover most npm publishing scenarios.\n# For complex dotted pre-releases (v1.0.0-alpha.beta.1), use simpler formats\n# like v1.0.0-alphabeta1 or create the workflow manually.\n"on":\n  push:\n    tags:\n      - \'v[0-9]+.[0-9]+.[0-9]+\'\n      - \'v[0-9]+.[0-9]+.[0-9]+-[a-zA-Z0-9]+\'\n      - \'v[0-9]+.[0-9]+.[0-9]+-[a-zA-Z0-9]+.[0-9]+\'\n\n# Permissions for NPM trusted publishing with provenance\npermissions:\n  contents: read\n  id-token: write\n\njobs:\n  publish:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@08c6903cd8c0fde910a37f88322edcfb5dd907a8 # v5\n      \n      - name: Setup Node.js\n        uses: actions/setup-node@2028fbc5c25fe9cf00d9f06a71cc4710d4507903 #v6\n        with:\n          node-version: 22\n\n      - name: Install npm@latest\n        run: npm install -g npm@latest\n      \n      - name: Install dependencies\n        run: npm ci\n      \n      - name: Publish to NPM\n        run: npm publish\n',
        }
