"""
Parameterized generator for GH256_next.js_90920.

Source PR:    https://github.com/vercel/next.js/pull/90920
Source Issue: N/A

Seed varies: renames 'absolutely' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH256_next.js_90920'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH256_next.js_90920'
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
                files[fpath] = files[fpath].replace('absolutely', 'absolutely' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH256_next.js_90920',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'vercel/next.js',
                "pr_number": 90920,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/vercel/next.js/pull/90920",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'errors/large-page-data.mdx': '---\ntitle: Large Page Data\n---\n\n## Why This Error Occurred\n\nOne of your pages includes a large amount of page data (>= 128kB). This can negatively impact performance since page data must be parsed by the client before the page is hydrated.\n\n## Possible Ways to Fix It\n\nReduce the amount of data returned from `getStaticProps`, `getServerSideProps`, or `getInitialProps` to only the essential data to render the page. The default threshold of 128kB can be configured in `largePageDataBytes` if absolutely necessary and the performance implications are understood.\n\nTo inspect the props passed to your page, you can inspect the below element\'s content in your browser devtools:\n\n```bash filename="Terminal"\nJSON.parse(document.getElementById("__NEXT_DATA__").textContent)\n```\n\n## Useful Links\n\n- [Data Fetching Documentation](/docs/pages/building-your-application/data-fetching)\n',
        }
