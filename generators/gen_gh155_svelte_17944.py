"""
Parameterized generator for GH155_svelte_17944.

Source PR:    https://github.com/sveltejs/svelte/pull/17944
Source Issue: https://github.com/sveltejs/svelte/issues/17730

Seed varies: renames 'anchor' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH155_svelte_17944'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH155_svelte_17944'
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
                files[fpath] = files[fpath].replace('anchor', 'anchor' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH155_svelte_17944',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'sveltejs/svelte',
                "pr_number": 17944,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/sveltejs/svelte/pull/17944",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'packages/svelte/src/compiler/phases/3-transform/client/visitors/Fragment.js': "/** @import { Expression, Statement } from 'estree' */\n/** @import { AST } from '#compiler' */\n/** @import { ComponentClientTransformState, ComponentContext } from '../types' */\nimport * as b from '#compiler/builders';\nimport { TEMPLATE_FRAGMENT, TEMPLATE_USE_IMPORT_NODE } from '../../../../../constants.js';\nimport { clean_nodes, infer_namespace } from '../../utils.js';\nimport { transform_template } from '../transform-template/index.js';\nimport { Template } from '../transform-template/template.js';\nimport { process_children } from './shared/fragment.js';\nimport { build_render_statement, Memoizer } from './shared/utils.js';\n\n/**\n * @param {AST.Fragment} node\n * @param {ComponentContext} context\n */\nexport function Fragment(node, context) {\n\t// Creates a new block which looks roughly like this:\n\t// ```js\n\t// // hoisted:\n\t// const block_name = $.from_html(`...`);\n\t//\n\t// // for the main block:\n\t// const id = block_name();\n\t// // init stuff and possibly render effect\n\t// $.append($$anchor, id);\n\t// ```\n\t// Adds the hoisted parts to `context.state.hoisted` and returns the statements of the main block.\n\n\tconst parent = context.path.at(-1) ?? node;\n\n\tconst namespace = infer_namespace(context.state.metadata.namespace, parent, node.nodes);\n\n\tconst { hoisted, trimmed, is_standalone, is_text_first } = clean_nodes(\n\t\tparent,\n\t\tnode.nodes,\n\t\tcontext.path,\n\t\tnamespace,\n\t\tcontext.state,\n\t\tcontext.state.preserve_whitespace,\n\t\tcontext.state.options.preserveComments\n\t);\n\n\tif (hoisted.length === 0 && trimmed.length === 0) {\n\t\treturn b.block([]);\n\t}\n\n\tconst is_single_element = trimmed.length === 1 && trimmed[0].type === 'RegularElement';\n\tconst is_single_child_not_needing_template =\n\t\ttrimmed.length === 1 &&\n\t\t(trimmed[0].type === 'SvelteFragment' ||\n\t\t\ttrimmed[0].type === 'TitleElement' ||\n\t\t\t(trimmed[0].type === 'IfBlock' &&\n\t\t\t\ttrimmed[0].elseif &&\n\t\t\t\t/** @type {AST.IfBlock} */ (parent).metadata.flattened?.includes(trimmed[0])));\n\tconst template_name = context.state.scope.root.unique('root'); // TODO infer name from parent\n\n\t/** @type {Statement[]} */\n\tconst body = [];\n\n\t/** @type {Statement | undefined} */\n\tlet close = undefined;\n\n\t/** @type {ComponentClientTransformState} */\n\tconst state = {\n\t\t...context.state,\n\t\tinit: [],\n\t\tsnippets: [],\n\t\tconsts: [],\n\t\tlet_directives: [],\n\t\tupdate: [],\n\t\tafter_update: [],\n\t\tmemoizer: new Memoizer(),\n\t\ttemplate: new Template(),\n\t\ttransform: { ...context.state.transform },\n\t\tmetadata: {\n\t\t\tnamespace,\n\t\t\tbound_contenteditable: context.state.metadata.bound_contenteditable\n\t\t},\n\t\tasync_consts: undefined\n\t};\n\n\tfor (const node of hoisted) {\n\t\tcontext.visit(node, state);\n\t}\n\n\tif (is_single_element) {\n\t\tconst element = /** @type {AST.RegularElement} */ (trimmed[0]);\n\n\t\tconst id = b.id(context.state.scope.generate(element.name), element.name_loc);\n\n\t\tcontext.visit(element, {\n\t\t\t...state,\n\t\t\tnode: id\n\t\t});\n\n\t\tlet flags = state.template.needs_import_node ? TEMPLATE_USE_IMPORT_NODE : undefined;\n\n\t\tconst template = transform_template(state, namespace, flags);\n\t\tstate.hoisted.push(b.var(template_name, template));\n\n\t\tstate.init.unshift(b.var(id, b.call(template_name)));\n\t\tclose = b.stmt(b.call('$.append', b.id('$$anchor'), id));\n\t} else if (is_single_child_not_needing_template) {\n\t\tcontext.visit(trimmed[0], state);\n\t} else if (trimmed.length === 1 && trimmed[0].type === 'Text') {\n\t\tconst id = b.id(context.state.scope.generate('text'));\n\t\tstate.init.unshift(b.var(id, b.call('$.text', b.literal(trimmed[0].data))));\n\t\tclose = b.stmt(b.call('$.append', b.id('$$anchor'), id));\n\t} else if (trimmed.length > 0) {\n\t\tconst id = b.id(context.state.scope.generate('fragment'));\n\n\t\tconst use_space_template =\n\t\t\ttrimmed.some((node) => node.type === 'ExpressionTag') &&\n\t\t\ttrimmed.every((node) => node.type === 'Text' || node.type === 'ExpressionTag');\n\n\t\tif (use_space_template) {\n\t\t\t// special case — we can use `$.text` instead of creating a unique template\n\t\t\tconst id = b.id(context.state.scope.generate('text'));\n\n\t\t\tprocess_children(trimmed, () => id, false, {\n\t\t\t\t...context,\n\t\t\t\tstate\n\t\t\t});\n\n\t\t\tstate.init.unshift(b.var(id, b.call('$.text')));\n\t\t\tclose = b.stmt(b.call('$.append', b.id('$$anchor'), id));\n\t\t} else if (is_standalone) {\n\t\t\t// no need to create a template, we can just use the existing block's anchor\n\t\t\tprocess_children(trimmed, () => b.id('$$anchor'), false, {\n\t\t\t\t...context,\n\t\t\t\tstate: { ...state, is_standalone }\n\t\t\t});\n\t\t} else {\n\t\t\t/** @type {(is_text: boolean) => Expression} */\n\t\t\tconst expression = (is_text) => b.call('$.first_child', id, is_text && b.true);\n\n\t\t\tprocess_children(trimmed, expression, false, { ...context, state });\n\n\t\t\tlet flags = TEMPLATE_FRAGMENT;\n\n\t\t\tif (state.template.needs_import_node) {\n\t\t\t\tflags |= TEMPLATE_USE_IMPORT_NODE;\n\t\t\t}\n\n\t\t\tif (state.template.nodes.length === 1 && state.template.nodes[0].type === 'comment') {\n\t\t\t\t// special case — we can use `$.comment` instead of creating a unique template\n\t\t\t\tstate.init.unshift(b.var(id, b.call('$.comment')));\n\t\t\t} else {\n\t\t\t\tconst template = transform_template(state, namespace, flags);\n\t\t\t\tstate.hoisted.push(b.var(template_name, template));\n\n\t\t\t\tstate.init.unshift(b.var(id, b.call(template_name)));\n\t\t\t}\n\n\t\t\tclose = b.stmt(b.call('$.append', b.id('$$anchor'), id));\n\t\t}\n\t}\n\n\tbody.push(...state.snippets, ...state.let_directives, ...state.consts);\n\n\tif (state.async_consts && state.async_consts.thunks.length > 0) {\n\t\tbody.push(b.var(state.async_consts.id, b.call('$.run', b.array(state.async_consts.thunks))));\n\t}\n\n\tif (is_text_first) {\n\t\t// skip over inserted comment\n\t\tbody.push(b.stmt(b.call('$.next')));\n\t}\n\n\tbody.push(...state.init);\n\n\tif (state.update.length > 0) {\n\t\tbody.push(build_render_statement(state));\n\t}\n\n\tbody.push(...state.after_update);\n\n\tif (close !== undefined) {\n\t\t// It's important that close is the last statement in the block, as any previous statements\n\t\t// could contain element insertions into the template, which the close statement needs to\n\t\t// know of when constructing the list of current inner elements.\n\t\tbody.push(close);\n\t}\n\n\treturn b.block(body);\n}\n",
            'packages/svelte/tests/runtime-runes/samples/async-render-component-hydration/Image.svelte': '<script>\n\tlet { src } = $props();\n</script>\n\n<img {src} />\n',
            'packages/svelte/tests/runtime-runes/samples/async-render-component-hydration/Link.svelte': '<script>\n\tlet { children } = $props();\n</script>\n\n<a href="/">\n\t{@render children()}\n</a>\n',
            'packages/svelte/tests/runtime-runes/samples/async-render-component-hydration/_config.js': 'import { tick } from \'svelte\';\nimport { test } from \'../../test\';\n\nexport default test({\n\tmode: [\'hydrate\'],\n\n\tasync test({ assert, target }) {\n\t\tawait tick();\n\t\tassert.htmlEqual(\n\t\t\ttarget.innerHTML,\n\t\t\t`<a href="/"><div>card</div> <img src="https://svelte.dev" /></a>`\n\t\t);\n\t}\n});\n',
            'packages/svelte/tests/runtime-runes/samples/async-render-component-hydration/main.svelte': '<script lang="ts">\n\timport Image from "./Image.svelte";\n\timport Link from "./Link.svelte";\n\n\tlet url = $derived(await \'https://svelte.dev\');\n</script>\n\n<Link>\n\t<div>card</div>\n\t<Image src={url} />\n</Link>\n',
        }
