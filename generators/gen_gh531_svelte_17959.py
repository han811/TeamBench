"""
Parameterized generator for GH531_svelte_17959.

Source PR:    https://github.com/sveltejs/svelte/pull/17959
Source Issue: N/A

Seed varies: renames 'above' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH531_svelte_17959'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH531_svelte_17959'
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
                files[fpath] = files[fpath].replace('above', 'above' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH531_svelte_17959',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'sveltejs/svelte',
                "pr_number": 17959,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/sveltejs/svelte/pull/17959",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'documentation/docs/06-runtime/02-context.md': "---\ntitle: Context\n---\n\nContext allows components to access values owned by parent components without passing them down as props (potentially through many layers of intermediate components, known as 'prop-drilling'). The parent component sets context with `setContext(key, value)`...\n\n```svelte\n<!--- file: Parent.svelte --->\n<script>\n\timport { setContext } from 'svelte';\n\n\tsetContext('my-context', 'hello from Parent.svelte');\n</script>\n```\n\n...and the child retrieves it with `getContext`:\n\n```svelte\n<!--- file: Child.svelte --->\n<script>\n\timport { getContext } from 'svelte';\n\n\tconst message = getContext('my-context');\n</script>\n\n<h1>{message}, inside Child.svelte</h1>\n```\n\nThis is particularly useful when `Parent.svelte` is not directly aware of `Child.svelte`, but instead renders it as part of a `children` [snippet](snippet) ([demo](/playground/untitled#H4sIAAAAAAAAE42Q3W6DMAyFX8WyJgESK-oto6hTX2D3YxcM3IIUQpR40yqUd58CrCXsp7tL7HNsf2dAWXaEKR56yfTBGOOxFWQwfR6Qz8q1XAHjL-GjUhvzToJd7bU09FO9ctMkG0wxM5VuFeeFLLjtVK8ZnkpNkuGo-w6CTTJ9Z3PwsBAemlbUF934W8iy5DpaZtOUcU02-ZLcaS51jHEkTFm_kY1_wfOO8QnXrb8hBzDEc6pgZ4gFoyz4KgiD7nxfTe8ghqAhIfrJ46cTzVZBbkPlODVJsLCDO6V7ZcJoncyw1yRr0hd1GNn_ZbEM3I9i1bmVxOlWElUvDUNHxpQngt3C4CXzjS1rtvkw22wMrTRtTbC8Lkuabe7jvthPPe3DofYCAAA=)):\n\n```svelte\n<Parent>\n\t<Child />\n</Parent>\n```\n\nThe key (`'my-context'`, in the example above) and the context itself can be any JavaScript value.\n\nIn addition to [`setContext`](svelte#setContext) and [`getContext`](svelte#getContext), Svelte exposes [`hasContext`](svelte#hasContext) and [`getAllContexts`](svelte#getAllContexts) functions.\n\n## Using context with state\n\nYou can store reactive state in context ([demo](/playground/untitled#H4sIAAAAAAAAE41R0W6DMAz8FSuaBNUQdK8MkKZ-wh7HHihzu6hgosRMm1D-fUpSVNq12x4iEvvOx_kmQU2PIhfP3DCCJGgHYvxkkYid7NCI_GUS_KUcxhVEMjOelErNB3bsatvG4LW6n0ZsRC4K02qpuKqpZtmrQTNMYJA3QRAs7PTQQxS40eMCt3mX3duxnWb-lS5h7nTI0A4jMWoo4c44P_Hku-zrOazdy64chWo-ScfRkRgl8wgHKrLTH1OxHZkHgoHaTraHcopXUFYzPPVfuC_hwQaD1GrskdiNCdQwJljJqlvXfyqVsA5CGg0uRUQifHw56xFtciO75QrP07vo_JXf_tf8yK2ezDKY_ZWt_1y2qqYzv7bI1IW1V_sN19m-07wCAAA=))...\n\n```svelte\n<script>\n\timport { setContext } from 'svelte';\n\timport Child from './Child.svelte';\n\n\tlet counter = $state({\n\t\tcount: 0\n\t});\n\n\tsetContext('counter', counter);\n</script>\n\n<button onclick={() => counter.count += 1}>\n\tincrement\n</button>\n\n<Child />\n<Child />\n<Child />\n```\n\n...though note that if you _reassign_ `counter` instead of updating it, you will 'break the link' — in other words instead of this...\n\n```svelte\n<button onclick={() => counter = { count: 0 }}>\n\treset\n</button>\n```\n\n...you must do this:\n\n```svelte\n<button onclick={() => +++counter.count = 0+++}>\n\treset\n</button>\n```\n\nSvelte will warn you if you get it wrong.\n\n## Type-safe context\n\nAs an alternative to using `setContext` and `getContext` directly, you can use them via `createContext`. This gives you type safety and makes it unnecessary to use a key:\n\n```ts\n/// file: context.ts\n// @filename: ambient.d.ts\ninterface User {}\n\n// @filename: index.ts\n// ---cut---\nimport { createContext } from 'svelte';\n\nexport const [getUserContext, setUserContext] = createContext<User>();\n```\n\nWhen writing [component tests](testing#Unit-and-component-tests-with-Vitest-Component-testing), it can be useful to create a wrapper component that sets the context in order to check the behaviour of a component that uses it. As of version 5.49, you can do this sort of thing:\n\n```js\nimport { mount, unmount } from 'svelte';\nimport { expect, test } from 'vitest';\nimport { setUserContext } from './context';\nimport MyComponent from './MyComponent.svelte';\n\ntest('MyComponent', () => {\n\tfunction Wrapper(...args) {\n\t\tsetUserContext({ name: 'Bob' });\n\t\treturn MyComponent(...args);\n\t}\n\n\tconst component = mount(Wrapper, {\n\t\ttarget: document.body\n\t});\n\n\texpect(document.body.innerHTML).toBe('<h1>Hello Bob!</h1>');\n\n\tunmount(component);\n});\n```\n\nThis approach also works with [`hydrate`](imperative-component-api#hydrate) and [`render`](imperative-component-api#render).\n\n## Replacing global state\n\nWhen you have state shared by many different components, you might be tempted to put it in its own module and just import it wherever it's needed:\n\n```js\n/// file: state.svelte.js\nexport const myGlobalState = $state({\n\tuser: {\n\t\t// ...\n\t}\n\t// ...\n});\n```\n\nIn many cases this is perfectly fine, but there is a risk: if you mutate the state during server-side rendering (which is discouraged, but entirely possible!)...\n\n```svelte\n<!--- file: App.svelte ---->\n<script>\n\timport { myGlobalState } from './state.svelte.js';\n\n\tlet { data } = $props();\n\n\tif (data.user) {\n\t\tmyGlobalState.user = data.user;\n\t}\n</script>\n```\n\n...then the data may be accessible by the _next_ user. Context solves this problem because it is not shared between requests.\n",
        }
