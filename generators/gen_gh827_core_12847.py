"""
Parameterized generator for GH827_core_12847.

Source PR:    https://github.com/vuejs/core/pull/12847
Source Issue: N/A

Seed varies: renames 'child' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH827_core_12847'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH827_core_12847'
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
                files[fpath] = files[fpath].replace('child', 'child' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH827_core_12847',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'vuejs/core',
                "pr_number": 12847,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/vuejs/core/pull/12847",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'packages/compiler-vapor/__tests__/transforms/__snapshots__/transformChildren.spec.ts.snap': '// Vitest Snapshot v1, https://vitest.dev/guide/snapshot.html\n\nexports[`compiler: children transform > children & sibling references 1`] = `\n"import { child as _child, nextn as _nextn, next as _next, createTextNode as _createTextNode, insert as _insert, toDisplayString as _toDisplayString, setText as _setText, renderEffect as _renderEffect, template as _template } from \'vue\';\nconst t0 = _template("<div><p> </p> <!><p> </p></div>", true)\n\nexport function render(_ctx) {\n  const n4 = t0()\n  const n0 = _child(n4)\n  const n3 = _nextn(n0, 2)\n  const n2 = _next(n3)\n  const x0 = _child(n0)\n  const n1 = _createTextNode()\n  const x2 = _child(n2)\n  _insert(n1, n4, n3)\n  _renderEffect(() => {\n    _setText(x0, _toDisplayString(_ctx.first))\n    _setText(n1, _toDisplayString(_ctx.second) + " " + _toDisplayString(_ctx.third) + " ")\n    _setText(x2, _toDisplayString(_ctx.forth))\n  })\n  return n4\n}"\n`;\n\nexports[`compiler: children transform > efficient traversal 1`] = `\n"import { child as _child, next as _next, toDisplayString as _toDisplayString, setText as _setText, renderEffect as _renderEffect, template as _template } from \'vue\';\nconst t0 = _template("<div><div>x</div><div><span> </span></div><div><span> </span></div><div><span> </span></div></div>", true)\n\nexport function render(_ctx) {\n  const n3 = t0()\n  const p0 = _next(_child(n3))\n  const n0 = _child(p0)\n  const p1 = _next(p0)\n  const n1 = _child(p1)\n  const p2 = _next(p1)\n  const n2 = _child(p2)\n  const x0 = _child(n0)\n  const x1 = _child(n1)\n  const x2 = _child(n2)\n  _renderEffect(() => {\n    const _msg = _ctx.msg\n    \n    _setText(x0, _toDisplayString(_msg))\n    _setText(x1, _toDisplayString(_msg))\n    _setText(x2, _toDisplayString(_msg))\n  })\n  return n3\n}"\n`;\n',
            'packages/compiler-vapor/__tests__/transforms/transformChildren.spec.ts': "import { makeCompile } from './_utils'\nimport {\n  transformChildren,\n  transformElement,\n  transformText,\n  transformVIf,\n} from '../../src'\n\nconst compileWithElementTransform = makeCompile({\n  nodeTransforms: [\n    transformText,\n    transformVIf,\n    transformElement,\n    transformChildren,\n  ],\n})\n\ndescribe('compiler: children transform', () => {\n  test('children & sibling references', () => {\n    const { code, helpers } = compileWithElementTransform(\n      `<div>\n        <p>{{ first }}</p>\n        {{ second }}\n        {{ third }}\n        <p>{{ forth }}</p>\n      </div>`,\n    )\n    expect(code).toMatchSnapshot()\n    expect(Array.from(helpers)).containSubset([\n      'next',\n      'setText',\n      'createTextNode',\n      'insert',\n      'template',\n    ])\n  })\n\n  test('efficient traversal', () => {\n    const { code } = compileWithElementTransform(\n      `<div>\n    <div>x</div>\n    <div><span>{{ msg }}</span></div>\n    <div><span>{{ msg }}</span></div>\n    <div><span>{{ msg }}</span></div>\n  </div>`,\n    )\n    expect(code).toMatchSnapshot()\n  })\n})\n",
            'packages/compiler-vapor/src/generators/template.ts': 'import type { CodegenContext } from \'../generate\'\nimport { DynamicFlag, type IRDynamicInfo } from \'../ir\'\nimport { genDirectivesForElement } from \'./directive\'\nimport { type CodeFragment, NEWLINE, buildCodeFragment, genCall } from \'./utils\'\n\nexport function genTemplates(\n  templates: string[],\n  rootIndex: number | undefined,\n  { helper }: CodegenContext,\n): string {\n  return templates\n    .map(\n      (template, i) =>\n        `const t${i} = ${helper(\'template\')}(${JSON.stringify(\n          template,\n        )}${i === rootIndex ? \', true\' : \'\'})\\n`,\n    )\n    .join(\'\')\n}\n\nexport function genChildren(\n  dynamic: IRDynamicInfo,\n  context: CodegenContext,\n  from: string,\n  path: number[] = [],\n  knownPaths: [id: string, path: number[]][] = [],\n): CodeFragment[] {\n  const { helper } = context\n  const [frag, push] = buildCodeFragment()\n  let offset = 0\n  const { children, id, template } = dynamic\n\n  if (id !== undefined && template !== undefined) {\n    push(NEWLINE, `const n${id} = t${template}()`)\n    push(...genDirectivesForElement(id, context))\n  }\n\n  let prev: [variable: string, elementIndex: number] | undefined\n  for (const [index, child] of children.entries()) {\n    if (child.flags & DynamicFlag.NON_TEMPLATE) {\n      offset--\n    }\n\n    const id =\n      child.flags & DynamicFlag.REFERENCED\n        ? child.flags & DynamicFlag.INSERT\n          ? child.anchor\n          : child.id\n        : undefined\n\n    if (id === undefined && !child.hasDynamicChild) {\n      const { id, template } = child\n      if (id !== undefined && template !== undefined) {\n        push(NEWLINE, `const n${id} = t${template}()`)\n        push(...genDirectivesForElement(id, context))\n      }\n      continue\n    }\n\n    const elementIndex = Number(index) + offset\n    const newPath = [...path, elementIndex]\n\n    // p for "placeholder" variables that are meant for possible reuse by\n    // other access paths\n    const variable = id === undefined ? `p${context.block.tempId++}` : `n${id}`\n    push(NEWLINE, `const ${variable} = `)\n\n    if (prev) {\n      const offset = elementIndex - prev[1]\n      if (offset === 1) {\n        push(...genCall(helper(\'next\'), prev[0]))\n      } else {\n        push(...genCall(helper(\'nextn\'), prev[0], String(offset)))\n      }\n    } else {\n      if (newPath.length === 1 && newPath[0] === 0) {\n        push(...genCall(helper(\'child\'), from))\n      } else {\n        // check if there\'s a node that we can reuse from\n        let resolvedFrom = from\n        let resolvedPath = newPath\n        let skipFirstChild = false\n        outer: for (const [from, path] of knownPaths) {\n          const l = path.length\n          const tail = newPath.slice(l)\n          for (let i = 0; i < l; i++) {\n            const parentSeg = path[i]\n            const thisSeg = newPath[i]\n            if (parentSeg !== thisSeg) {\n              if (i === l - 1) {\n                // last bit is reusable\n                resolvedFrom = from\n                resolvedPath = [thisSeg - parentSeg, ...tail]\n                skipFirstChild = true\n                break outer\n              }\n              break\n            } else if (i === l - 1) {\n              // full overlap\n              resolvedFrom = from\n              resolvedPath = tail\n              break outer\n            }\n          }\n        }\n        let init\n        for (const i of resolvedPath) {\n          init = init\n            ? genCall(helper(\'child\'), init)\n            : skipFirstChild\n              ? resolvedFrom\n              : genCall(helper(\'child\'), resolvedFrom)\n          if (i === 1) {\n            init = genCall(helper(\'next\'), init)\n          } else if (i > 1) {\n            init = genCall(helper(\'nextn\'), init, String(i))\n          }\n        }\n        push(...init!)\n      }\n    }\n    if (id !== undefined) {\n      push(...genDirectivesForElement(id, context))\n    }\n    knownPaths.unshift([variable, newPath])\n    prev = [variable, elementIndex]\n    push(...genChildren(child, context, variable))\n  }\n\n  return frag\n}\n',
            'packages/runtime-vapor/__tests__/dom/template.spec.ts': "import { template } from '../../src/dom/template'\nimport { child, next, nextn } from '../../src/dom/node'\n\ndescribe('api: template', () => {\n  test('create element', () => {\n    const t = template('<div>')\n    const root = t()\n    expect(root).toBeInstanceOf(HTMLDivElement)\n\n    const root2 = t()\n    expect(root2).toBeInstanceOf(HTMLDivElement)\n    expect(root2).not.toBe(root)\n  })\n\n  test('create root element', () => {\n    const t = template('<div>', true)\n    const root = t()\n    expect(root.$root).toBe(true)\n  })\n\n  test('next', () => {\n    const t = template('<div><span></span><b></b><p></p></div>')\n    const root = t()\n    const span = child(root as ParentNode)\n    const b = next(span)\n\n    expect(span).toBe(root.childNodes[0])\n    expect(b).toBe(root.childNodes[1])\n    expect(nextn(span, 2)).toBe(root.childNodes[2])\n    expect(next(b)).toBe(root.childNodes[2])\n  })\n})\n",
            'packages/runtime-vapor/src/dom/node.ts': "/*! #__NO_SIDE_EFFECTS__ */\nexport function createTextNode(value = ''): Text {\n  return document.createTextNode(value)\n}\n\n/*! #__NO_SIDE_EFFECTS__ */\nexport function createComment(data: string): Comment {\n  return document.createComment(data)\n}\n\n/*! #__NO_SIDE_EFFECTS__ */\nexport function querySelector(selectors: string): Element | null {\n  return document.querySelector(selectors)\n}\n\n/*! #__NO_SIDE_EFFECTS__ */\nexport function child(node: ParentNode): Node {\n  return node.firstChild!\n}\n\n/*! #__NO_SIDE_EFFECTS__ */\nexport function next(node: Node): Node {\n  return node.nextSibling!\n}\n\n/*! #__NO_SIDE_EFFECTS__ */\nexport function nextn(node: Node, offset: number = 1): Node {\n  for (let i = 0; i < offset; i++) {\n    node = node.nextSibling!\n  }\n  return node\n}\n",
            'packages/runtime-vapor/src/index.ts': "// public APIs\nexport { createVaporApp } from './apiCreateApp'\nexport { defineVaporComponent } from './apiDefineComponent'\nexport { vaporInteropPlugin } from './vdomInterop'\nexport type { VaporDirective } from './directives/custom'\n\n// compiler-use only\nexport { insert, prepend, remove } from './block'\nexport { createComponent, createComponentWithFallback } from './component'\nexport { renderEffect } from './renderEffect'\nexport { createSlot } from './componentSlots'\nexport { template } from './dom/template'\nexport { createTextNode, child, next, nextn } from './dom/node'\nexport {\n  setText,\n  setHtml,\n  setClass,\n  setStyle,\n  setAttr,\n  setValue,\n  setProp,\n  setDOMProp,\n  setDynamicProps,\n} from './dom/prop'\nexport { on, delegate, delegateEvents, setDynamicEvents } from './dom/event'\nexport { createIf } from './apiCreateIf'\nexport {\n  createFor,\n  createForSlots,\n  getRestElement,\n  getDefaultValue,\n} from './apiCreateFor'\nexport { createTemplateRefSetter } from './apiTemplateRef'\nexport { createDynamicComponent } from './apiCreateDynamicComponent'\nexport { applyVShow } from './directives/vShow'\nexport {\n  applyTextModel,\n  applyRadioModel,\n  applyCheckboxModel,\n  applySelectModel,\n  applyDynamicModel,\n} from './directives/vModel'\nexport { withVaporDirectives } from './directives/custom'\n",
        }
