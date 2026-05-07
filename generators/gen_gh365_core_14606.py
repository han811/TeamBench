"""
Parameterized generator for GH365_core_14606.

Source PR:    https://github.com/vuejs/core/pull/14606
Source Issue: N/A

Seed varies: renames 'also' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH365_core_14606'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH365_core_14606'
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
                files[fpath] = files[fpath].replace('also', 'also' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH365_core_14606',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'vuejs/core',
                "pr_number": 14606,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/vuejs/core/pull/14606",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'packages/compiler-vapor/__tests__/transforms/TransformTransition.spec.ts': 'import { makeCompile } from \'./_utils\'\nimport {\n  transformChildren,\n  transformElement,\n  transformKey,\n  transformText,\n  transformVBind,\n  transformVIf,\n  transformVShow,\n  transformVSlot,\n} from \'@vue/compiler-vapor\'\nimport { transformTransition } from \'../../src/transforms/transformTransition\'\nimport { DOMErrorCodes } from \'@vue/compiler-dom\'\n\nconst compileWithElementTransform = makeCompile({\n  nodeTransforms: [\n    transformText,\n    transformVIf,\n    transformKey,\n    transformElement,\n    transformVSlot,\n    transformChildren,\n    transformTransition,\n  ],\n  directiveTransforms: {\n    bind: transformVBind,\n    show: transformVShow,\n  },\n})\n\ndescribe(\'compiler: transition\', () => {\n  test(\'basic\', () => {\n    const { code } = compileWithElementTransform(\n      `<Transition><h1 v-show="show">foo</h1></Transition>`,\n    )\n    expect(code).toMatchSnapshot()\n  })\n\n  test(\'v-show + appear\', () => {\n    const { code } = compileWithElementTransform(\n      `<Transition appear><h1 v-show="show">foo</h1></Transition>`,\n    )\n    expect(code).toMatchSnapshot()\n  })\n\n  test(\'work with v-if\', () => {\n    const { code } = compileWithElementTransform(\n      `<Transition><h1 v-if="show">foo</h1></Transition>`,\n    )\n\n    expect(code).toMatchSnapshot()\n  })\n\n  test(\'work with dynamic keyed children\', () => {\n    const { code } = compileWithElementTransform(\n      `<Transition>\n        <h1 :key="key">foo</h1>\n      </Transition>`,\n    )\n\n    expect(code).toMatchSnapshot()\n    expect(code).contains(\'_createKeyedFragment(() => (_ctx.key)\')\n  })\n\n  function checkWarning(template: string, shouldWarn = true) {\n    const onError = vi.fn()\n    compileWithElementTransform(template, { onError })\n    if (shouldWarn) {\n      expect(onError).toHaveBeenCalled()\n      expect(onError.mock.calls).toMatchObject([\n        [{ code: DOMErrorCodes.X_TRANSITION_INVALID_CHILDREN }],\n      ])\n    } else {\n      expect(onError).not.toHaveBeenCalled()\n    }\n  }\n\n  test(\'warns if multiple children\', () => {\n    checkWarning(\n      `<Transition>\n        <h1>foo</h1>\n        <h2>bar</h2>\n      </Transition>`,\n      true,\n    )\n  })\n\n  test(\'warns with v-for\', () => {\n    checkWarning(\n      `\n      <transition>\n        <div v-for="i in items">hey</div>\n      </transition>\n      `,\n      true,\n    )\n  })\n\n  test(\'warns with multiple v-if + v-for\', () => {\n    checkWarning(\n      `\n      <transition>\n        <div v-if="a" v-for="i in items">hey</div>\n        <div v-else v-for="i in items">hey</div>\n      </transition>\n      `,\n      true,\n    )\n  })\n\n  test(\'warns with template v-if\', () => {\n    checkWarning(\n      `\n      <transition>\n        <template v-if="ok"></template>\n      </transition>\n      `,\n      true,\n    )\n  })\n\n  test(\'warns with multiple templates\', () => {\n    checkWarning(\n      `\n      <transition>\n        <template v-if="a"></template>\n        <template v-else></template>\n      </transition>\n      `,\n      true,\n    )\n  })\n\n  test(\'warns if multiple children with v-if\', () => {\n    checkWarning(\n      `\n      <transition>\n        <div v-if="one">hey</div>\n        <div v-if="other">hey</div>\n      </transition>\n      `,\n      true,\n    )\n  })\n\n  test(\'does not warn with regular element\', () => {\n    checkWarning(\n      `\n      <transition>\n        <div>hey</div>\n      </transition>\n      `,\n      false,\n    )\n  })\n\n  test(\'does not warn with one single v-if\', () => {\n    checkWarning(\n      `\n      <transition>\n        <div v-if="a">hey</div>\n      </transition>\n      `,\n      false,\n    )\n  })\n\n  test(\'does not warn with v-if v-else-if v-else\', () => {\n    checkWarning(\n      `\n      <transition>\n        <div v-if="a">hey</div>\n        <div v-else-if="b">hey</div>\n        <div v-else>hey</div>\n      </transition>\n      `,\n      false,\n    )\n  })\n\n  test(\'does not warn with v-if v-else\', () => {\n    checkWarning(\n      `\n      <transition>\n        <div v-if="a">hey</div>\n        <div v-else>hey</div>\n      </transition>\n      `,\n      false,\n    )\n  })\n\n  test(\'does not warn with multiple children in v-if branch\', () => {\n    checkWarning(\n      `\n      <transition>\n        <h1 v-if="condition">\n          <span>True</span>\n          <span>True</span>\n        </h1>\n        <h1 v-else>False</h1>\n      </transition>\n      `,\n      false,\n    )\n  })\n\n  test(\'inject persisted when child has v-show\', () => {\n    expect(\n      compileWithElementTransform(`\n        <Transition>\n          <div v-show="ok" />\n        </Transition>\n    `).code,\n    ).toMatchSnapshot()\n  })\n\n  test(\'the v-if/else-if/else branches in Transition should ignore comments\', () => {\n    expect(\n      compileWithElementTransform(`\n    <transition>\n      <div v-if="a">hey</div>\n      <!-- this should be ignored -->\n      <div v-else-if="b">hey</div>\n      <!-- this should be ignored -->\n      <div v-else>\n        <p v-if="c"/>\n        <!-- this should not be ignored -->\n        <p v-else/>\n      </div>\n    </transition>\n    `).code,\n    ).toMatchSnapshot()\n  })\n})\n',
            'packages/compiler-vapor/src/transforms/transformTransition.ts': "import type { NodeTransform } from '@vue/compiler-vapor'\nimport { findDir, isTransitionTag } from '../utils'\nimport {\n  type ElementNode,\n  ElementTypes,\n  NodeTypes,\n  isTemplateNode,\n  postTransformTransition,\n} from '@vue/compiler-dom'\n\nexport const transformTransition: NodeTransform = (node, context) => {\n  if (\n    node.type === NodeTypes.ELEMENT &&\n    node.tagType === ElementTypes.COMPONENT\n  ) {\n    if (isTransitionTag(node.tag)) {\n      return postTransformTransition(\n        node,\n        context.options.onError,\n        hasMultipleChildren,\n      )\n    }\n  }\n}\n\nfunction hasMultipleChildren(node: ElementNode): boolean {\n  const children = (node.children = node.children.filter(\n    c =>\n      c.type !== NodeTypes.COMMENT &&\n      !(c.type === NodeTypes.TEXT && !c.content.trim()),\n  ))\n\n  const first = children[0]\n\n  // has v-for\n  if (\n    children.length === 1 &&\n    first.type === NodeTypes.ELEMENT &&\n    (findDir(first, 'for') || isTemplateNode(first))\n  ) {\n    return true\n  }\n\n  const hasElse = (node: ElementNode) =>\n    findDir(node, 'else-if') || findDir(node, 'else', true)\n\n  // has v-if/v-else-if/v-else\n  if (\n    children.every(\n      (c, index) =>\n        c.type === NodeTypes.ELEMENT &&\n        // not template\n        !isTemplateNode(c) &&\n        // not has v-for\n        !findDir(c, 'for') &&\n        // if the first child has v-if, the rest should also have v-else-if/v-else\n        (index === 0 ? findDir(c, 'if') : hasElse(c)),\n    )\n  ) {\n    return false\n  }\n\n  return children.length > 1\n}\n",
        }
