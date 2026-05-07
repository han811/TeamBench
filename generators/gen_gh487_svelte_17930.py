"""
Parameterized generator for GH487_svelte_17930.

Source PR:    https://github.com/sveltejs/svelte/pull/17930
Source Issue: N/A

Seed varies: renames 'allows' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH487_svelte_17930'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH487_svelte_17930'
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
                files[fpath] = files[fpath].replace('allows', 'allows' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH487_svelte_17930',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'sveltejs/svelte',
                "pr_number": 17930,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/sveltejs/svelte/pull/17930",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'packages/svelte/tests/runtime-runes/samples/untrack-allows-writes/_config.js': 'import { flushSync } from \'svelte\';\nimport { test } from \'../../test\';\n\n// While we don\'t officially document it, `untrack` also allows to opt out of the "unsafe mutation" validation, which is what we test here\nexport default test({\n\thtml: \'<button>0 0 0</button>\',\n\ttest({ assert, target }) {\n\t\tconst button = target.querySelector(\'button\');\n\n\t\tflushSync(() => button?.click());\n\n\t\tassert.htmlEqual(\n\t\t\ttarget.innerHTML,\n\t\t\t`\n\t\t\t\t<button>1 1 2</button>\n\t\t\t`\n\t\t);\n\t}\n});\n',
            'packages/svelte/tests/runtime-runes/samples/untrack-allows-writes/main.svelte': '<script>\n\timport { untrack } from "svelte";\n\n\tlet count = $state(0);\n\tlet mirrored = $state(0);\n\tlet double = $derived.by(() => {\n\t\tuntrack(() => {\n\t\t\tmirrored = count;\n\t\t});\n\t\treturn count * 2;\n\t})\n</script>\n\n<button onclick={() => count++}>{count} {mirrored} {double}</button>\n',
        }
