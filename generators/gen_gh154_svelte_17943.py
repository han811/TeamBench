"""
Parameterized generator for GH154_svelte_17943.

Source PR:    https://github.com/sveltejs/svelte/pull/17943
Source Issue: https://github.com/sveltejs/svelte/issues/17514

Seed varies: renames 'after' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH154_svelte_17943'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH154_svelte_17943'
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
            task_id='GH154_svelte_17943',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'sveltejs/svelte',
                "pr_number": 17943,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/sveltejs/svelte/pull/17943",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'packages/svelte/src/compiler/phases/3-transform/shared/transform-async.js': "/** @import * as ESTree from 'estree' */\n/** @import { ComponentAnalysis } from '../../types' */\nimport * as b from '#compiler/builders';\n\n/**\n * Transforms the body of the instance script in such a way that await expressions are made non-blocking as much as possible.\n *\n * Example Transformation:\n * ```js\n * let x = 1;\n * let data = await fetch('/api');\n * let y = data.value;\n * ```\n * becomes:\n * ```js\n * let x = 1;\n * var data, y;\n * var $$promises = $.run([\n *   () => data = await fetch('/api'),\n *   () => y = data.value\n * ]);\n * ```\n * where `$$promises` is an array of promises that are resolved in the order they are declared,\n * and which expressions in the template can await on like `await $$promises[0]` which means they\n * wouldn't have to wait for e.g. `$$promises[1]` to resolve.\n *\n * @param {ComponentAnalysis['instance_body']} instance_body\n * @param {ESTree.Expression} runner\n * @param {(node: ESTree.Node) => ESTree.Node} transform\n * @returns {Array<ESTree.Statement | ESTree.VariableDeclaration>}\n */\nexport function transform_body(instance_body, runner, transform) {\n\t// Any sync statements before the first await expression\n\tconst statements = instance_body.sync.map(\n\t\t(node) => /** @type {ESTree.Statement | ESTree.VariableDeclaration} */ (transform(node))\n\t);\n\n\t// Declarations for the await expressions (they will assign to them; need to be hoisted to be available in whole instance scope)\n\tif (instance_body.declarations.length > 0) {\n\t\tstatements.push(\n\t\t\tb.declaration(\n\t\t\t\t'var',\n\t\t\t\tinstance_body.declarations.map((id) => b.declarator(id))\n\t\t\t)\n\t\t);\n\t}\n\n\t// Thunks for the await expressions\n\tif (instance_body.async.length > 0) {\n\t\tconst thunks = instance_body.async.map((s) => {\n\t\t\tif (s.node.type === 'VariableDeclarator') {\n\t\t\t\tconst visited = /** @type {ESTree.VariableDeclaration | ESTree.EmptyStatement} */ (\n\t\t\t\t\ttransform(b.var(s.node.id, s.node.init))\n\t\t\t\t);\n\n\t\t\t\tconst statements =\n\t\t\t\t\tvisited.type === 'VariableDeclaration'\n\t\t\t\t\t\t? visited.declarations.map((node) => {\n\t\t\t\t\t\t\t\tif (\n\t\t\t\t\t\t\t\t\tnode.id.type === 'Identifier' &&\n\t\t\t\t\t\t\t\t\t(node.id.name.startsWith('$$d') || node.id.name.startsWith('$$array'))\n\t\t\t\t\t\t\t\t) {\n\t\t\t\t\t\t\t\t\t// this is an intermediate declaration created in VariableDeclaration.js;\n\t\t\t\t\t\t\t\t\t// subsequent statements depend on it\n\t\t\t\t\t\t\t\t\treturn b.var(node.id, node.init);\n\t\t\t\t\t\t\t\t}\n\n\t\t\t\t\t\t\t\treturn b.stmt(b.assignment('=', node.id, node.init ?? b.void0));\n\t\t\t\t\t\t\t})\n\t\t\t\t\t\t: [];\n\n\t\t\t\tif (statements.length === 1) {\n\t\t\t\t\tconst statement = /** @type {ESTree.ExpressionStatement} */ (statements[0]);\n\t\t\t\t\treturn b.thunk(statement.expression, s.has_await);\n\t\t\t\t}\n\n\t\t\t\treturn b.thunk(b.block(statements), s.has_await);\n\t\t\t}\n\n\t\t\tif (s.node.type === 'ClassDeclaration') {\n\t\t\t\treturn b.thunk(\n\t\t\t\t\tb.assignment(\n\t\t\t\t\t\t'=',\n\t\t\t\t\t\ts.node.id,\n\t\t\t\t\t\t/** @type {ESTree.ClassExpression} */ ({ ...s.node, type: 'ClassExpression' })\n\t\t\t\t\t),\n\t\t\t\t\ts.has_await\n\t\t\t\t);\n\t\t\t}\n\n\t\t\tif (s.node.type === 'ExpressionStatement') {\n\t\t\t\t// the expression may be a $inspect call, which will be transformed into an empty statement\n\t\t\t\tconst expression = /** @type {ESTree.Expression | ESTree.EmptyStatement} */ (\n\t\t\t\t\ttransform(s.node.expression)\n\t\t\t\t);\n\n\t\t\t\tif (expression.type === 'EmptyStatement') {\n\t\t\t\t\treturn null;\n\t\t\t\t}\n\n\t\t\t\treturn expression.type === 'AwaitExpression'\n\t\t\t\t\t? b.thunk(expression, true)\n\t\t\t\t\t: b.thunk(b.unary('void', expression), s.has_await);\n\t\t\t}\n\n\t\t\treturn b.thunk(b.block([/** @type {ESTree.Statement} */ (transform(s.node))]), s.has_await);\n\t\t});\n\n\t\t// TODO get the `$$promises` ID from scope\n\t\tstatements.push(b.var('$$promises', b.call(runner, b.array(thunks))));\n\t}\n\n\treturn statements;\n}\n",
            'packages/svelte/tests/runtime-runes/samples/async-inspect-build/_config.js': "import { tick } from 'svelte';\nimport { test } from '../../test';\n\nexport default test({\n\tssrHtml: 'works',\n\tasync test({ assert, target }) {\n\t\tawait tick();\n\t\tassert.htmlEqual(target.innerHTML, 'works');\n\t}\n});\n",
            'packages/svelte/tests/runtime-runes/samples/async-inspect-build/main.svelte': '<script lang="ts">\n  const test = async () => "test";\n  await test();\n  $inspect("inspect after await shouldnt break builds");\n</script>\n\nworks\n',
            'packages/svelte/tests/snapshot/samples/async-top-level-inspect-server/_expected/client/index.svelte.js': "import 'svelte/internal/disclose-version';\nimport 'svelte/internal/flags/async';\nimport * as $ from 'svelte/internal/client';\n\nvar root = $.from_html(`<p> </p>`);\n\nexport default function Async_top_level_inspect_server($$anchor) {\n\tvar data;\n\tvar $$promises = $.run([async () => data = await Promise.resolve(42),,]);\n\tvar p = root();\n\tvar text = $.child(p, true);\n\n\t$.reset(p);\n\t$.template_effect(() => $.set_text(text, data), void 0, void 0, [$$promises[1]]);\n\t$.append($$anchor, p);\n}",
            'packages/svelte/tests/snapshot/samples/async-top-level-inspect-server/_expected/server/index.svelte.js': "import 'svelte/internal/flags/async';\nimport * as $ from 'svelte/internal/server';\n\nexport default function Async_top_level_inspect_server($$renderer) {\n\tvar data;\n\tvar $$promises = $$renderer.run([async () => data = await Promise.resolve(42),,]);\n\n\t$$renderer.push(`<p>`);\n\t$$renderer.async([$$promises[1]], ($$renderer) => $$renderer.push(() => $.escape(data)));\n\t$$renderer.push(`</p>`);\n}",
        }
