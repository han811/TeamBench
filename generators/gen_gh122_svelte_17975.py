"""
Parameterized generator for GH122_svelte_17975.

Source PR:    https://github.com/sveltejs/svelte/pull/17975
Source Issue: https://github.com/sveltejs/svelte/issues/17972

Seed varies: renames 'after' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH122_svelte_17975'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH122_svelte_17975'
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
                files[fpath] = files[fpath].replace('after', 'after' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH122_svelte_17975',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'sveltejs/svelte',
                "pr_number": 17975,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/sveltejs/svelte/pull/17975",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'packages/svelte/src/internal/client/dev/hmr.js': "/** @import { Effect, TemplateNode } from '#client' */\nimport { FILENAME, HMR } from '../../../constants.js';\nimport { EFFECT_TRANSPARENT } from '#client/constants';\nimport { hydrate_node, hydrating } from '../dom/hydration.js';\nimport { block, branch, destroy_effect } from '../reactivity/effects.js';\nimport { set, source } from '../reactivity/sources.js';\nimport { set_should_intro } from '../render.js';\nimport { get } from '../runtime.js';\nimport { assign_nodes } from '../dom/template.js';\nimport { create_comment } from '../dom/operations.js';\n\n/**\n * @template {(anchor: Comment, props: any) => any} Component\n * @param {Component} fn\n */\nexport function hmr(fn) {\n\tconst current = source(fn);\n\n\t/**\n\t * @param {TemplateNode} anchor\n\t * @param {any} props\n\t */\n\tfunction wrapper(anchor, props) {\n\t\tlet component = {};\n\t\tlet instance = {};\n\n\t\t/** @type {Effect} */\n\t\tlet effect;\n\n\t\tlet ran = false;\n\n\t\t// Surround the wrapped effects with comments and assign the nodes\n\t\t// on the wrapping effects so the parent can properly do DOM operations.\n\t\tlet start = create_comment();\n\t\tlet end = create_comment();\n\n\t\tanchor.before(start);\n\n\t\tblock(() => {\n\t\t\tif (component === (component = get(current))) {\n\t\t\t\treturn;\n\t\t\t}\n\n\t\t\tif (effect) {\n\t\t\t\t// @ts-ignore\n\t\t\t\tfor (var k in instance) delete instance[k];\n\t\t\t\tdestroy_effect(effect);\n\t\t\t}\n\n\t\t\teffect = branch(() => {\n\t\t\t\t// when the component is invalidated, replace it without transitions\n\t\t\t\tif (ran) set_should_intro(false);\n\n\t\t\t\t// preserve getters/setters\n\t\t\t\tObject.defineProperties(\n\t\t\t\t\tinstance,\n\t\t\t\t\tObject.getOwnPropertyDescriptors(\n\t\t\t\t\t\t// @ts-expect-error\n\t\t\t\t\t\tnew.target ? new component(anchor, props) : component(anchor, props)\n\t\t\t\t\t)\n\t\t\t\t);\n\n\t\t\t\tif (ran) set_should_intro(true);\n\t\t\t});\n\t\t}, EFFECT_TRANSPARENT);\n\n\t\tran = true;\n\n\t\tif (hydrating) {\n\t\t\tanchor = hydrate_node;\n\t\t}\n\n\t\tanchor.before(end);\n\n\t\tassign_nodes(start, end);\n\n\t\treturn instance;\n\t}\n\n\t// @ts-expect-error\n\twrapper[FILENAME] = fn[FILENAME];\n\n\t// @ts-ignore\n\twrapper[HMR] = {\n\t\tfn,\n\t\tcurrent,\n\t\tupdate: (/** @type {any} */ incoming) => {\n\t\t\t// This logic ensures that the first version of the component is the one\n\t\t\t// whose update function and therefore block effect is preserved across updates.\n\t\t\t// If we don't do this dance and instead just use `incoming` as the new component\n\t\t\t// and then update, we'll create an ever-growing stack of block effects.\n\n\t\t\t// Trigger the original block effect\n\t\t\tset(wrapper[HMR].current, incoming[HMR].fn);\n\n\t\t\t// Replace the incoming source with the original one\n\t\t\tincoming[HMR].current = wrapper[HMR].current;\n\t\t}\n\t};\n\n\treturn wrapper;\n}\n",
            'packages/svelte/tests/hydration/samples/css-props-hmr/Component.svelte': '<h1>Hello</h1>\n\n<style>\n\th1 {\n\t\tcolor: var(--color);\n\t}\n</style>',
            'packages/svelte/tests/hydration/samples/css-props-hmr/_config.js': "import { test } from '../../test';\n\nexport default test({\n\tcompileOptions: {\n\t\thmr: true\n\t}\n});\n",
            'packages/svelte/tests/hydration/samples/css-props-hmr/main.svelte': '<script>\n\timport Component from "./Component.svelte";\n</script>\n\n<Component --color="red" />',
        }
