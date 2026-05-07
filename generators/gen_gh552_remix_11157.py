"""
Parameterized generator for GH552_remix_11157.

Source PR:    https://github.com/remix-run/remix/pull/11157
Source Issue: N/A

Seed varies: renames 'abort' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH552_remix_11157'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH552_remix_11157'
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
                files[fpath] = files[fpath].replace('abort', 'abort' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH552_remix_11157',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'remix-run/remix',
                "pr_number": 11157,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/remix-run/remix/pull/11157",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'packages/component/src/lib/navigation.ts': "import { getTopFrame, getNamedFrame } from './run.ts'\n\ntype NavigationState = {\n  target: string | undefined\n  src: string\n  resetScroll: boolean\n  $rmx: true\n}\n\ntype SourceElementNavigateEvent = NavigateEvent & {\n  sourceElement?: Element | null\n}\n\n/**\n * Options for client-side frame-aware navigation.\n */\nexport type NavigationOptions = {\n  src?: string\n  target?: string\n  history?: 'push' | 'replace'\n  resetScroll?: boolean\n}\n\n/**\n * Performs a Navigation API transition understood by Remix frame runtime state.\n *\n * @param href Destination URL.\n * @param options Navigation options.\n */\nexport async function navigate(href: string, options?: NavigationOptions) {\n  let state = {\n    target: options?.target,\n    src: options?.src ?? href,\n    resetScroll: options?.resetScroll !== false,\n    $rmx: true,\n  } satisfies NavigationState\n  let transition = window.navigation.navigate(href, { state, history: options?.history })\n  await transition.finished\n}\n\n/**\n * Starts listening for Navigation API transitions and routes them through frame reloads.\n *\n * @param signal Abort signal used to remove the listener.\n */\nexport function startNavigationListener(signal: AbortSignal) {\n  let navigation = window.navigation\n\n  navigation.updateCurrentEntry({\n    state: { target: undefined, src: window.location.href, resetScroll: true, $rmx: true },\n  })\n\n  navigation.addEventListener(\n    'navigate',\n    (event) => {\n      if (!event.canIntercept) return\n\n      let state = getRuntimeNavigationState(event)\n      if (!state) return\n\n      let topFrame = getTopFrame()\n      let namedFrame = state.target ? getNamedFrame(state.target) : undefined\n      let frame = namedFrame ?? topFrame\n\n      event.intercept({\n        async handler() {\n          if (event.navigationType !== 'traverse') {\n            navigation.updateCurrentEntry({ state })\n          }\n\n          frame.src = frame === topFrame ? event.destination.url : state.src\n          await frame.reload()\n\n          let isNewEntry = event.navigationType === 'push' || event.navigationType === 'replace'\n          if (state.resetScroll && isNewEntry) {\n            window.scrollTo(0, 0)\n          }\n        },\n      })\n    },\n    { signal },\n  )\n}\n\nfunction isRuntimeNavigation(info: unknown): info is NavigationState {\n  return typeof info === 'object' && info != null && '$rmx' in info\n}\n\nfunction getRuntimeNavigationState(event: NavigateEvent): NavigationState | undefined {\n  if (event.navigationType === 'traverse') {\n    return getTraverseNavigationState(event)\n  }\n\n  let sourceState = getSourceElementNavigationState(event)\n  if (sourceState) return sourceState\n\n  let destinationState = event.destination.getState()\n  if (isRuntimeNavigation(destinationState)) return destinationState\n}\n\nfunction getTraverseNavigationState(event: NavigateEvent): NavigationState | undefined {\n  let destinationState = event.destination.getState()\n  if (isRuntimeNavigation(destinationState)) {\n    return destinationState\n  }\n\n  // Safari returns `null` for destination.getState(), even though its in the\n  // navigation.entries(), so we do its job for it and look it up.\n  let navigation = window.navigation\n  let matchingEntry = navigation.entries().find((entry) => entry.key === event.destination.key)\n  if (matchingEntry) {\n    let state = matchingEntry.getState()\n    if (isRuntimeNavigation(state)) {\n      return state\n    }\n  }\n\n  return undefined\n}\n\nfunction getSourceElementNavigationState(event: NavigateEvent): NavigationState | undefined {\n  let sourceEvent = event as SourceElementNavigateEvent\n  let sourceElement = sourceEvent.sourceElement\n  if (!(sourceElement instanceof Element)) return\n  if (!sourceElement.matches('a, area')) return\n  if (sourceElement.hasAttribute('rmx-document')) return\n\n  return {\n    target: sourceElement.getAttribute('rmx-target') ?? undefined,\n    src: sourceElement.getAttribute('rmx-src') ?? event.destination.url,\n    resetScroll: sourceElement.getAttribute('rmx-reset-scroll') !== 'false',\n    $rmx: true,\n  } satisfies NavigationState\n}\n",
            'packages/component/src/test/navigation.test.ts': "import { afterEach, describe, expect, it, vi } from 'vitest'\n\nimport { navigate, startNavigationListener } from '../lib/navigation.ts'\n\ndescribe('navigate', () => {\n  afterEach(() => {\n    document.body.innerHTML = ''\n    vi.unstubAllGlobals()\n  })\n\n  it('passes runtime state via navigate history state', async () => {\n    let navigateMock = vi.fn(() => ({ finished: Promise.resolve() }))\n    vi.stubGlobal('navigation', { navigate: navigateMock })\n\n    await navigate('/login', {\n      src: '/partials/login',\n      target: 'auth',\n      history: 'replace',\n    })\n\n    expect(navigateMock).toHaveBeenCalledWith('/login', {\n      state: { target: 'auth', src: '/partials/login', resetScroll: true, $rmx: true },\n      history: 'replace',\n    })\n  })\n\n  it('passes resetScroll=false when requested', async () => {\n    let navigateMock = vi.fn(() => ({ finished: Promise.resolve() }))\n    vi.stubGlobal('navigation', { navigate: navigateMock })\n\n    await navigate('/login', {\n      resetScroll: false,\n    })\n\n    expect(navigateMock).toHaveBeenCalledWith('/login', {\n      state: { target: undefined, src: '/login', resetScroll: false, $rmx: true },\n      history: undefined,\n    })\n  })\n\n  it('does not intercept anchors marked for document navigation', () => {\n    let navigation = Object.assign(new EventTarget(), {\n      navigate: vi.fn(() => ({ finished: Promise.resolve() })),\n      updateCurrentEntry: vi.fn(),\n    })\n    vi.stubGlobal('navigation', navigation)\n\n    let controller = new AbortController()\n    startNavigationListener(controller.signal)\n\n    let anchor = document.createElement('a')\n    anchor.href = '/login'\n    anchor.setAttribute('rmx-document', '')\n    document.body.append(anchor)\n    anchor.addEventListener('click', (event) => event.preventDefault())\n\n    let clickEvent = new MouseEvent('click', { bubbles: true, cancelable: true })\n    anchor.dispatchEvent(clickEvent)\n\n    expect(navigation.navigate).not.toHaveBeenCalled()\n    expect(clickEvent.defaultPrevented).toBe(true)\n\n    anchor.remove()\n    controller.abort()\n  })\n})\n",
        }
