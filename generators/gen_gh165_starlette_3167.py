"""
Parameterized generator for GH165_starlette_3167.

Source PR:    https://github.com/Kludex/starlette/pull/3167
Source Issue: N/A

Seed varies: renames 'actions' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH165_starlette_3167'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH165_starlette_3167'
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
            task_id='GH165_starlette_3167',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'Kludex/starlette',
                "pr_number": 3167,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/Kludex/starlette/pull/3167",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            '.github/workflows/main.yml': '---\nname: Test Suite\n\non:\n  push:\n    branches: ["main"]\n  pull_request:\n    branches: ["main"]\n\njobs:\n  tests:\n    name: "Python ${{ matrix.python-version }}"\n    runs-on: ubuntu-latest\n\n    strategy:\n      matrix:\n        python-version: ["3.10", "3.11", "3.12", "3.13", "3.14"]\n\n    steps:\n      - uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd # v6.0.2\n\n      - name: Install uv\n        uses: astral-sh/setup-uv@803947b9bd8e9f986429fa0c5a41c367cd732b41 # v7.2.1\n        with:\n          python-version: ${{ matrix.python-version }}\n          enable-cache: true\n\n      - name: Install dependencies\n        run: scripts/install\n\n      - name: Run linting checks\n        run: scripts/check\n        if: ${{ matrix.python-version != \'3.14\' }}\n\n      - name: "Build package & docs"\n        run: scripts/build\n\n      - name: "Run tests"\n        run: scripts/test\n\n      - name: "Enforce coverage"\n        run: scripts/coverage\n\n  # https://github.com/marketplace/actions/alls-green#why\n  check:\n    if: always()\n    needs: [tests]\n    runs-on: ubuntu-latest\n    steps:\n      - name: Decide whether the needed jobs succeeded or failed\n        uses: re-actors/alls-green@05ac9388f0aebcb5727afa17fcccfecd6f8ec5fe # v1.2.2\n        with:\n          jobs: ${{ toJSON(needs) }}\n',
            '.github/workflows/publish.yml': 'name: Publish\n\non:\n  push:\n    tags:\n      - "*"\n  workflow_dispatch:\n\njobs:\n  build:\n    runs-on: ubuntu-latest\n\n    steps:\n      - uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd # v6.0.2\n\n      - name: Install uv\n        uses: astral-sh/setup-uv@803947b9bd8e9f986429fa0c5a41c367cd732b41 # v7.2.1\n        with:\n          python-version: "3.11"\n          enable-cache: true\n\n      - name: Install dependencies\n        run: scripts/install\n\n      - name: Build package & docs\n        run: scripts/build\n\n      - name: Upload package distributions\n        uses: actions/upload-artifact@b7c566a772e6b6bfb58ed0dc250532a479d7789f # v6.0.0\n        with:\n          name: package-distributions\n          path: dist/\n\n      - name: Upload documentation\n        uses: actions/upload-artifact@b7c566a772e6b6bfb58ed0dc250532a479d7789f # v6.0.0\n        with:\n          name: documentation\n          path: site/\n\n  pypi-publish:\n    runs-on: ubuntu-latest\n    needs: build\n    if: success() && startsWith(github.ref, \'refs/tags/\')\n\n    permissions:\n      id-token: write\n\n    environment:\n      name: pypi\n      url: https://pypi.org/project/starlette\n\n    steps:\n      - name: Download artifacts\n        uses: actions/download-artifact@37930b1c2abaa49bbe596cd826c3c89aef350131 # v7.0.0\n        with:\n          name: package-distributions\n          path: dist/\n\n      - name: Publish distribution 📦 to PyPI\n        uses: pypa/gh-action-pypi-publish@ed0c53931b1dc9bd32cbe73a98c7f6766f8a527e # v1.13.0\n\n  docs-publish:\n    runs-on: ubuntu-latest\n    needs: build\n\n    permissions:\n      contents: read\n      pages: write\n      id-token: write\n\n    environment:\n      name: github-pages\n      url: ${{ steps.deployment.outputs.page_url }}\n\n    steps:\n      - name: Configure GitHub Pages\n        uses: actions/configure-pages@983d7736d9b0ae728b81ab479565c72886d7745b # v5.0.0\n\n      - name: Download artifacts\n        uses: actions/download-artifact@37930b1c2abaa49bbe596cd826c3c89aef350131 # v7.0.0\n        with:\n          name: documentation\n          path: site/\n\n      - name: Upload Pages artifact\n        uses: actions/upload-pages-artifact@7b1f4a764d45c48632c6b24a0339c27f5614fb0b # v4.0.0\n        with:\n          path: site\n\n      - name: Deploy to GitHub Pages\n        uses: actions/deploy-pages@d6db90164ac5ed86f2b6aed7e0febac5b3c0c03e # v4.0.5\n        id: deployment\n\n  docs-cloudflare:\n    runs-on: ubuntu-latest\n    needs: build\n\n    environment:\n      name: cloudflare\n      url: https://starlette.dev\n\n    steps:\n      - uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd # v6.0.2\n      - name: Download artifacts\n        uses: actions/download-artifact@37930b1c2abaa49bbe596cd826c3c89aef350131 # v7.0.0\n        with:\n          name: documentation\n          path: site/\n\n      - uses: cloudflare/wrangler-action@da0e0dfe58b7a431659754fdf3f186c529afbe65 # v3.14.1\n        with:\n          apiToken: ${{ secrets.CLOUDFLARE_API_TOKEN }}\n          command: >\n            pages deploy ./site\n            --project-name starlette\n            --commit-hash ${{ github.sha }}\n            --branch main\n',
        }
