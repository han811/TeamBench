"""
Parameterized generator for GH805_jinja_2105.

Source PR:    https://github.com/pallets/jinja/pull/2105
Source Issue: N/A

Seed varies: renames 'actions' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH805_jinja_2105'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH805_jinja_2105'
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
            task_id='GH805_jinja_2105',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'pallets/jinja',
                "pr_number": 2105,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/pallets/jinja/pull/2105",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            '.github/workflows/publish.yaml': 'name: Publish\non:\n  push:\n    tags:\n      - \'*\'\njobs:\n  build:\n    runs-on: ubuntu-latest\n    outputs:\n      hash: ${{ steps.hash.outputs.hash }}\n    steps:\n      - uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683 # v4.2.2\n      - uses: actions/setup-python@0b93645e9fea7318ecaed2b359559ac225c90a2b # v5.3.0\n        with:\n          python-version: \'3.x\'\n          cache: pip\n          cache-dependency-path: requirements*/*.txt\n      - run: pip install -r requirements/build.txt\n      # Use the commit date instead of the current date during the build.\n      - run: echo "SOURCE_DATE_EPOCH=$(git log -1 --pretty=%ct)" >> $GITHUB_ENV\n      - run: python -m build\n      # Generate hashes used for provenance.\n      - name: generate hash\n        id: hash\n        run: cd dist && echo "hash=$(sha256sum * | base64 -w0)" >> $GITHUB_OUTPUT\n      - uses: actions/upload-artifact@6f51ac03b9356f520e9adb1b1b7802705f340c2b # v4.5.0\n        with:\n          path: ./dist\n  provenance:\n    needs: [build]\n    permissions:\n      actions: read\n      id-token: write\n      contents: write\n    # Can\'t pin with hash due to how this workflow works.\n    uses: slsa-framework/slsa-github-generator/.github/workflows/generator_generic_slsa3.yml@v2.0.0\n    with:\n      base64-subjects: ${{ needs.build.outputs.hash }}\n  create-release:\n    # Upload the sdist, wheels, and provenance to a GitHub release. They remain\n    # available as build artifacts for a while as well.\n    needs: [provenance]\n    runs-on: ubuntu-latest\n    permissions:\n      contents: write\n    steps:\n      - uses: actions/download-artifact@fa0a91b85d4f404e444e00e005971372dc801d16 # v4.1.8\n      - name: create release\n        run: >\n          gh release create --draft --repo ${{ github.repository }}\n          ${{ github.ref_name }}\n          *.intoto.jsonl/* artifact/*\n        env:\n          GH_TOKEN: ${{ github.token }}\n  publish-pypi:\n    needs: [provenance]\n    # Wait for approval before attempting to upload to PyPI. This allows reviewing the\n    # files in the draft release.\n    environment:\n      name: publish\n      url: https://pypi.org/project/Jinja2/${{ github.ref_name }}\n    runs-on: ubuntu-latest\n    permissions:\n      id-token: write\n    steps:\n      - uses: actions/download-artifact@fa0a91b85d4f404e444e00e005971372dc801d16 # v4.1.8\n      - uses: pypa/gh-action-pypi-publish@67339c736fd9354cd4f8cb0b744f2b82a74b5c70 # v1.12.3\n        with:\n          packages-dir: artifact/\n',
        }
