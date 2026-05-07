"""
Parameterized generator for GH264_core_12308.

Source PR:    https://github.com/vuejs/core/pull/12308
Source Issue: N/A

Seed varies: renames 'array' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH264_core_12308'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH264_core_12308'
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
                files[fpath] = files[fpath].replace('array', 'array' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH264_core_12308',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'vuejs/core',
                "pr_number": 12308,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/vuejs/core/pull/12308",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'packages/runtime-core/__tests__/helpers/renderList.spec.ts': 'import {\n  effect,\n  isReactive,\n  reactive,\n  readonly,\n  shallowReactive,\n} from \'../../src/index\'\nimport { renderList } from \'../../src/helpers/renderList\'\n\ndescribe(\'renderList\', () => {\n  it(\'should render items in an array\', () => {\n    expect(\n      renderList([\'1\', \'2\', \'3\'], (item, index) => `node ${index}: ${item}`),\n    ).toEqual([\'node 0: 1\', \'node 1: 2\', \'node 2: 3\'])\n  })\n\n  it(\'should render characters of a string\', () => {\n    expect(\n      renderList(\'123\', (item, index) => `node ${index}: ${item}`),\n    ).toEqual([\'node 0: 1\', \'node 1: 2\', \'node 2: 3\'])\n  })\n\n  it(\'should render integers 1 through N when given a number N\', () => {\n    expect(renderList(3, (item, index) => `node ${index}: ${item}`)).toEqual([\n      \'node 0: 1\',\n      \'node 1: 2\',\n      \'node 2: 3\',\n    ])\n  })\n\n  it(\'should warn when given a non-integer N\', () => {\n    try {\n      renderList(3.1, () => {})\n    } catch (e) {}\n    expect(\n      `The v-for range expect an integer value but got 3.1.`,\n    ).toHaveBeenWarned()\n  })\n\n  it(\'should render properties in an object\', () => {\n    expect(\n      renderList(\n        { a: 1, b: 2, c: 3 },\n        (item, key, index) => `node ${index}/${key}: ${item}`,\n      ),\n    ).toEqual([\'node 0/a: 1\', \'node 1/b: 2\', \'node 2/c: 3\'])\n  })\n\n  it(\'should render an item for entry in an iterable\', () => {\n    const iterable = function* () {\n      yield 1\n      yield 2\n      yield 3\n    }\n\n    expect(\n      renderList(iterable(), (item, index) => `node ${index}: ${item}`),\n    ).toEqual([\'node 0: 1\', \'node 1: 2\', \'node 2: 3\'])\n  })\n\n  it(\'should return empty array when source is undefined\', () => {\n    expect(\n      renderList(undefined, (item, index) => `node ${index}: ${item}`),\n    ).toEqual([])\n  })\n\n  it(\'should render items in a reactive array correctly\', () => {\n    const reactiveArray = reactive([{ foo: 1 }])\n    expect(renderList(reactiveArray, isReactive)).toEqual([true])\n\n    const shallowReactiveArray = shallowReactive([{ foo: 1 }])\n    expect(renderList(shallowReactiveArray, isReactive)).toEqual([false])\n  })\n\n  it(\'should not allow mutation\', () => {\n    const arr = readonly(reactive([{ foo: 1 }]))\n    expect(\n      renderList(arr, item => {\n        ;(item as any).foo = 0\n        return item.foo\n      }),\n    ).toEqual([1])\n    expect(\n      `Set operation on key "foo" failed: target is readonly.`,\n    ).toHaveBeenWarned()\n  })\n\n  it(\'should trigger effect for deep mutations in readonly reactive arrays\', () => {\n    const arr = reactive([{ foo: 1 }])\n    const readonlyArr = readonly(arr)\n\n    let dummy\n    effect(() => {\n      dummy = renderList(readonlyArr, item => item.foo)\n    })\n    expect(dummy).toEqual([1])\n\n    arr[0].foo = 2\n    expect(dummy).toEqual([2])\n  })\n})\n',
            'packages/runtime-core/src/helpers/renderList.ts': "import type { VNode, VNodeChild } from '../vnode'\nimport {\n  isReactive,\n  isReadonly,\n  isShallow,\n  shallowReadArray,\n  toReactive,\n  toReadonly,\n} from '@vue/reactivity'\nimport { isArray, isObject, isString } from '@vue/shared'\nimport { warn } from '../warning'\n\n/**\n * v-for string\n * @private\n */\nexport function renderList(\n  source: string,\n  renderItem: (value: string, index: number) => VNodeChild,\n): VNodeChild[]\n\n/**\n * v-for number\n */\nexport function renderList(\n  source: number,\n  renderItem: (value: number, index: number) => VNodeChild,\n): VNodeChild[]\n\n/**\n * v-for array\n */\nexport function renderList<T>(\n  source: T[],\n  renderItem: (value: T, index: number) => VNodeChild,\n): VNodeChild[]\n\n/**\n * v-for iterable\n */\nexport function renderList<T>(\n  source: Iterable<T>,\n  renderItem: (value: T, index: number) => VNodeChild,\n): VNodeChild[]\n\n/**\n * v-for object\n */\nexport function renderList<T>(\n  source: T,\n  renderItem: <K extends keyof T>(\n    value: T[K],\n    key: string,\n    index: number,\n  ) => VNodeChild,\n): VNodeChild[]\n\n/**\n * Actual implementation\n */\nexport function renderList(\n  source: any,\n  renderItem: (...args: any[]) => VNodeChild,\n  cache?: any[],\n  index?: number,\n): VNodeChild[] {\n  let ret: VNodeChild[]\n  const cached = (cache && cache[index!]) as VNode[] | undefined\n  const sourceIsArray = isArray(source)\n\n  if (sourceIsArray || isString(source)) {\n    const sourceIsReactiveArray = sourceIsArray && isReactive(source)\n    let needsWrap = false\n    let isReadonlySource = false\n    if (sourceIsReactiveArray) {\n      needsWrap = !isShallow(source)\n      isReadonlySource = isReadonly(source)\n      source = shallowReadArray(source)\n    }\n    ret = new Array(source.length)\n    for (let i = 0, l = source.length; i < l; i++) {\n      ret[i] = renderItem(\n        needsWrap\n          ? isReadonlySource\n            ? toReadonly(toReactive(source[i]))\n            : toReactive(source[i])\n          : source[i],\n        i,\n        undefined,\n        cached && cached[i],\n      )\n    }\n  } else if (typeof source === 'number') {\n    if (__DEV__ && !Number.isInteger(source)) {\n      warn(`The v-for range expect an integer value but got ${source}.`)\n    }\n    ret = new Array(source)\n    for (let i = 0; i < source; i++) {\n      ret[i] = renderItem(i + 1, i, undefined, cached && cached[i])\n    }\n  } else if (isObject(source)) {\n    if (source[Symbol.iterator as any]) {\n      ret = Array.from(source as Iterable<any>, (item, i) =>\n        renderItem(item, i, undefined, cached && cached[i]),\n      )\n    } else {\n      const keys = Object.keys(source)\n      ret = new Array(keys.length)\n      for (let i = 0, l = keys.length; i < l; i++) {\n        const key = keys[i]\n        ret[i] = renderItem(source[key], key, i, cached && cached[i])\n      }\n    }\n  } else {\n    ret = []\n  }\n\n  if (cache) {\n    cache[index!] = ret\n  }\n  return ret\n}\n",
            'packages/server-renderer/__tests__/ssrRenderList.spec.ts': "import { ssrRenderList } from '../src/helpers/ssrRenderList'\n\ndescribe('ssr: renderList', () => {\n  let stack: string[] = []\n\n  beforeEach(() => {\n    stack = []\n  })\n\n  it('should render items in an array', () => {\n    ssrRenderList(['1', '2', '3'], (item, index) =>\n      stack.push(`node ${index}: ${item}`),\n    )\n    expect(stack).toEqual(['node 0: 1', 'node 1: 2', 'node 2: 3'])\n  })\n\n  it('should render characters of a string', () => {\n    ssrRenderList('abc', (item, index) => stack.push(`node ${index}: ${item}`))\n    expect(stack).toEqual(['node 0: a', 'node 1: b', 'node 2: c'])\n  })\n\n  it('should render integers 1 through N when given a number N', () => {\n    ssrRenderList(3, (item, index) => stack.push(`node ${index}: ${item}`))\n    expect(stack).toEqual(['node 0: 1', 'node 1: 2', 'node 2: 3'])\n  })\n\n  it('should warn when given a non-integer N', () => {\n    ssrRenderList(3.1, () => {})\n    expect(\n      `The v-for range expect an integer value but got 3.1.`,\n    ).toHaveBeenWarned()\n  })\n\n  it('should render properties in an object', () => {\n    ssrRenderList({ a: 1, b: 2, c: 3 }, (item, key, index) =>\n      stack.push(`node ${index}/${key}: ${item}`),\n    )\n    expect(stack).toEqual(['node 0/a: 1', 'node 1/b: 2', 'node 2/c: 3'])\n  })\n\n  it('should render an item for entry in an iterable', () => {\n    const iterable = function* () {\n      yield 1\n      yield 2\n      yield 3\n    }\n\n    ssrRenderList(iterable(), (item, index) =>\n      stack.push(`node ${index}: ${item}`),\n    )\n    expect(stack).toEqual(['node 0: 1', 'node 1: 2', 'node 2: 3'])\n  })\n\n  it('should not render items when source is undefined', () => {\n    ssrRenderList(undefined, (item, index) =>\n      stack.push(`node ${index}: ${item}`),\n    )\n    expect(stack).toEqual([])\n  })\n})\n",
            'packages/server-renderer/src/helpers/ssrRenderList.ts': "import { isArray, isObject, isString } from '@vue/shared'\nimport { warn } from '@vue/runtime-core'\n\nexport function ssrRenderList(\n  source: unknown,\n  renderItem: (value: unknown, key: string | number, index?: number) => void,\n): void {\n  if (isArray(source) || isString(source)) {\n    for (let i = 0, l = source.length; i < l; i++) {\n      renderItem(source[i], i)\n    }\n  } else if (typeof source === 'number') {\n    if (__DEV__ && !Number.isInteger(source)) {\n      warn(`The v-for range expect an integer value but got ${source}.`)\n      return\n    }\n    for (let i = 0; i < source; i++) {\n      renderItem(i + 1, i)\n    }\n  } else if (isObject(source)) {\n    if (source[Symbol.iterator as any]) {\n      const arr = Array.from(source as Iterable<any>)\n      for (let i = 0, l = arr.length; i < l; i++) {\n        renderItem(arr[i], i)\n      }\n    } else {\n      const keys = Object.keys(source)\n      for (let i = 0, l = keys.length; i < l; i++) {\n        const key = keys[i]\n        renderItem(source[key], key, i)\n      }\n    }\n  }\n}\n",
        }
