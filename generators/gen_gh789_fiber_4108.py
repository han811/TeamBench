"""
Parameterized generator for GH789_fiber_4108.

Source PR:    https://github.com/gofiber/fiber/pull/4108
Source Issue: N/A

Seed varies: renames 'action' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH789_fiber_4108'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH789_fiber_4108'
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
            task_id='GH789_fiber_4108',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'gofiber/fiber',
                "pr_number": 4108,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/gofiber/fiber/pull/4108",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            '.github/workflows/benchmark.yml': 'on:\n  workflow_dispatch:\n  push:\n    branches:\n      - main\n    paths-ignore:\n      - "**/*.md"\n  pull_request:\n    paths-ignore:\n      - "**/*.md"\n\npermissions:\n  # deployments permission to deploy GitHub pages website\n  deployments: write\n  # contents permission to update benchmark contents in gh-pages branch\n  contents: write\n  # allow posting comments to pull request\n  pull-requests: write\n\nname: Benchmark\njobs:\n  Compare:\n    runs-on: ubuntu-latest\n    steps:\n      - name: Fetch Repository\n        uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd # v6.0.2\n        with:\n          fetch-depth: 0 # to be able to retrieve the last commit in main\n\n      - name: Install Go\n        uses: actions/setup-go@4b73464bb391d4059bd26b0524d20df3927bd417 # v6.3.0\n        with:\n          # NOTE: Keep this in sync with the version from go.mod\n          go-version: "1.25.x"\n\n      - name: Run Benchmark\n        run: set -o pipefail; go test ./... -benchmem -run=^$ -bench . | tee output.txt\n      ### hack because of the problem with duplicated benchmark names - https://github.com/benchmark-action/github-action-benchmark/issues/264\n      - name: Extract Module Name\n        id: extract-module\n        run: |\n          MODULE_NAME=$(awk \'/^module / {print $2}\' go.mod)\n          echo "MODULE_NAME=$MODULE_NAME" >> $GITHUB_ENV\n\n      - name: Identify Duplicate Benchmark Names\n        run: |\n          awk \'/^Benchmark/ {print $1}\' output.txt | sort | uniq -d > duplicate_benchmarks.txt\n\n      - name: Add Normalized Package Prefix to Duplicate Benchmark Names\n        run: |\n          awk -v MODULE_NAME="$MODULE_NAME" \'\n            FNR==NR {duplicates[$1]; next}\n            /^pkg: / { package=$2 }\n            /^Benchmark/ {\n              if ($1 in duplicates) {\n                sub("^" MODULE_NAME "/?", "", package)\n                gsub("/", "_", package)\n                print $1 "_" package substr($0, length($1) + 1)\n              } else {\n                print $0\n              }\n              next\n            }\n            { print }\n          \' duplicate_benchmarks.txt output.txt > output_prefixed.txt\n          mv output_prefixed.txt output.txt\n      ### end\n\n      - name: Remove _Parallel Benchmarks\n        run: |\n          awk \'!/^Benchmark.*_Parallel/\' output.txt > output_filtered.txt\n          mv output_filtered.txt output.txt\n\n      # NOTE: Benchmarks could change with different CPU types\n      - name: Get GitHub Runner System Information\n        uses: kenchan0130/actions-system-info@59699597e84e80085a750998045983daa49274c4 # v1.4.0\n        id: system-info\n\n      - name: Get Main branch SHA\n        id: get-main-branch-sha\n        run: |\n          SHA=$(git rev-parse origin/main)\n          echo "sha=$SHA" >> $GITHUB_OUTPUT\n\n      - name: Get Benchmark Results from main branch\n        id: cache\n        uses: actions/cache/restore@cdf6c1fa76f9f475f3d7449005a359c84ca0f306 # v5.0.3\n        with:\n          path: ./cache\n          key: ${{ steps.get-main-branch-sha.outputs.sha }}-${{ runner.os }}-${{ steps.system-info.outputs.cpu-model }}-benchmark\n\n      # This will only run if we have Benchmark Results from main branch\n      - name: Compare PR Benchmark Results with main branch\n        uses: benchmark-action/github-action-benchmark@a7bc2366eda11037936ea57d811a43b3418d3073 # v1.21.0\n        if: steps.cache.outputs.cache-hit == \'true\'\n        with:\n          tool: \'go\'\n          output-file-path: output.txt\n          external-data-json-path: ./cache/benchmark-data.json\n          # Do not save the data (This allows comparing benchmarks)\n          save-data-file: false\n          fail-on-alert: true\n          # Comment on the PR if the branch is not a fork\n          comment-on-alert: ${{ github.event.pull_request.head.repo.fork == false }}\n          github-token: ${{ secrets.GITHUB_TOKEN }}\n          summary-always: true\n          alert-threshold: "150%"\n\n      - name: Store Benchmark Results for main branch\n        uses: benchmark-action/github-action-benchmark@a7bc2366eda11037936ea57d811a43b3418d3073 # v1.21.0\n        if: ${{ github.ref_name == \'main\' }}\n        with:\n          tool: \'go\'\n          output-file-path: output.txt\n          external-data-json-path: ./cache/benchmark-data.json\n          # Save the data to external file (cache)\n          save-data-file: true\n          fail-on-alert: false\n          github-token: ${{ secrets.GITHUB_TOKEN }}\n          summary-always: true\n          alert-threshold: "150%"\n\n      - name: Publish Benchmark Results to GitHub Pages\n        uses: benchmark-action/github-action-benchmark@a7bc2366eda11037936ea57d811a43b3418d3073 # v1.21.0\n        if: ${{ github.ref_name == \'main\' }}\n        with:\n          tool: \'go\'\n          output-file-path: output.txt\n          benchmark-data-dir-path: "benchmarks"\n          fail-on-alert: false\n          github-token: ${{ secrets.GITHUB_TOKEN }}\n          comment-on-alert: true\n          summary-always: true\n          # Save the data to external file (GitHub Pages)\n          save-data-file: true\n          alert-threshold: "150%"\n          auto-push: ${{ github.event_name == \'push\' || github.event_name == \'workflow_dispatch\' }}\n\n      - name: Update Benchmark Results cache\n        uses: actions/cache/save@cdf6c1fa76f9f475f3d7449005a359c84ca0f306 # v5.0.3\n        if: ${{ github.ref_name == \'main\' }}\n        with:\n          path: ./cache\n          key: ${{ steps.get-main-branch-sha.outputs.sha }}-${{ runner.os }}-${{ steps.system-info.outputs.cpu-model }}-benchmark\n',
        }
