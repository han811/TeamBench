"""
Parameterized generator for GH150_svelte_17966.

Source PR:    https://github.com/sveltejs/svelte/pull/17966
Source Issue: https://github.com/sveltejs/svelte/issues/16610

Seed varies: renames 'abrupt' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH150_svelte_17966'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH150_svelte_17966'
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
                files[fpath] = files[fpath].replace('abrupt', 'abrupt' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH150_svelte_17966',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'sveltejs/svelte',
                "pr_number": 17966,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/sveltejs/svelte/pull/17966",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'packages/svelte/src/internal/client/reactivity/async.js': '/** @import { Blocker, Effect, Value } from \'#client\' */\nimport { DESTROYED, STALE_REACTION } from \'#client/constants\';\nimport { DEV } from \'esm-env\';\nimport {\n\tcomponent_context,\n\tdev_stack,\n\tis_runes,\n\tset_component_context,\n\tset_dev_stack\n} from \'../context.js\';\nimport { Boundary } from \'../dom/blocks/boundary.js\';\nimport { invoke_error_boundary } from \'../error-handling.js\';\nimport {\n\tactive_effect,\n\tactive_reaction,\n\tset_active_effect,\n\tset_active_reaction\n} from \'../runtime.js\';\nimport { Batch, current_batch } from \'./batch.js\';\nimport {\n\tasync_derived,\n\treactivity_loss_tracker,\n\tderived,\n\tderived_safe_equal,\n\tset_reactivity_loss_tracker\n} from \'./deriveds.js\';\nimport { aborted } from \'./effects.js\';\n\n/**\n * @param {Blocker[]} blockers\n * @param {Array<() => any>} sync\n * @param {Array<() => Promise<any>>} async\n * @param {(values: Value[]) => any} fn\n */\nexport function flatten(blockers, sync, async, fn) {\n\tconst d = is_runes() ? derived : derived_safe_equal;\n\n\t// Filter out already-settled blockers - no need to wait for them\n\tvar pending = blockers.filter((b) => !b.settled);\n\n\tif (async.length === 0 && pending.length === 0) {\n\t\tfn(sync.map(d));\n\t\treturn;\n\t}\n\n\tvar parent = /** @type {Effect} */ (active_effect);\n\n\tvar restore = capture();\n\tvar blocker_promise =\n\t\tpending.length === 1\n\t\t\t? pending[0].promise\n\t\t\t: pending.length > 1\n\t\t\t\t? Promise.all(pending.map((b) => b.promise))\n\t\t\t\t: null;\n\n\t/** @param {Value[]} values */\n\tfunction finish(values) {\n\t\trestore();\n\n\t\ttry {\n\t\t\tfn(values);\n\t\t} catch (error) {\n\t\t\tif ((parent.f & DESTROYED) === 0) {\n\t\t\t\tinvoke_error_boundary(error, parent);\n\t\t\t}\n\t\t}\n\n\t\tunset_context();\n\t}\n\n\t// Fast path: blockers but no async expressions\n\tif (async.length === 0) {\n\t\t/** @type {Promise<any>} */ (blocker_promise).then(() => finish(sync.map(d)));\n\t\treturn;\n\t}\n\n\tvar decrement_pending = increment_pending();\n\n\t// Full path: has async expressions\n\tfunction run() {\n\t\tPromise.all(async.map((expression) => async_derived(expression)))\n\t\t\t.then((result) => finish([...sync.map(d), ...result]))\n\t\t\t.catch((error) => invoke_error_boundary(error, parent))\n\t\t\t.finally(() => decrement_pending());\n\t}\n\n\tif (blocker_promise) {\n\t\tblocker_promise.then(() => {\n\t\t\trestore();\n\t\t\trun();\n\t\t\tunset_context();\n\t\t});\n\t} else {\n\t\trun();\n\t}\n}\n\n/**\n * @param {Blocker[]} blockers\n * @param {(values: Value[]) => any} fn\n */\nexport function run_after_blockers(blockers, fn) {\n\tflatten(blockers, [], [], fn);\n}\n\n/**\n * Captures the current effect context so that we can restore it after\n * some asynchronous work has happened (so that e.g. `await a + b`\n * causes `b` to be registered as a dependency).\n */\nexport function capture() {\n\tvar previous_effect = /** @type {Effect} */ (active_effect);\n\tvar previous_reaction = active_reaction;\n\tvar previous_component_context = component_context;\n\tvar previous_batch = /** @type {Batch} */ (current_batch);\n\n\tif (DEV) {\n\t\tvar previous_dev_stack = dev_stack;\n\t}\n\n\treturn function restore(activate_batch = true) {\n\t\tset_active_effect(previous_effect);\n\t\tset_active_reaction(previous_reaction);\n\t\tset_component_context(previous_component_context);\n\n\t\tif (activate_batch && (previous_effect.f & DESTROYED) === 0) {\n\t\t\t// TODO we only need optional chaining here because `{#await ...}` blocks\n\t\t\t// are anomalous. Once we retire them we can get rid of it\n\t\t\tprevious_batch?.activate();\n\t\t\tprevious_batch?.apply();\n\t\t}\n\n\t\tif (DEV) {\n\t\t\tset_reactivity_loss_tracker(null);\n\t\t\tset_dev_stack(previous_dev_stack);\n\t\t}\n\t};\n}\n\n/**\n * Wraps an `await` expression in such a way that the effect context that was\n * active before the expression evaluated can be reapplied afterwards —\n * `await a + b` becomes `(await $.save(a))() + b`\n * @template T\n * @param {Promise<T>} promise\n * @returns {Promise<() => T>}\n */\nexport async function save(promise) {\n\tvar restore = capture();\n\tvar value = await promise;\n\n\treturn () => {\n\t\trestore();\n\t\treturn value;\n\t};\n}\n\n/**\n * Reset `current_async_effect` after the `promise` resolves, so\n * that we can emit `await_reactivity_loss` warnings\n * @template T\n * @param {Promise<T>} promise\n * @returns {Promise<() => T>}\n */\nexport async function track_reactivity_loss(promise) {\n\tvar previous_async_effect = reactivity_loss_tracker;\n\tvar value = await promise;\n\n\treturn () => {\n\t\tset_reactivity_loss_tracker(previous_async_effect);\n\t\treturn value;\n\t};\n}\n\n/**\n * Used in `for await` loops in DEV, so\n * that we can emit `await_reactivity_loss` warnings\n * after each `async_iterator` result resolves and\n * after the `async_iterator` return resolves (if it runs)\n * @template T\n * @template TReturn\n * @param {Iterable<T> | AsyncIterable<T>} iterable\n * @returns {AsyncGenerator<T, TReturn | undefined>}\n */\nexport async function* for_await_track_reactivity_loss(iterable) {\n\t// This is based on the algorithms described in ECMA-262:\n\t// ForIn/OfBodyEvaluation\n\t// https://tc39.es/ecma262/multipage/ecmascript-language-statements-and-declarations.html#sec-runtime-semantics-forin-div-ofbodyevaluation-lhs-stmt-iterator-lhskind-labelset\n\t// AsyncIteratorClose\n\t// https://tc39.es/ecma262/multipage/abstract-operations.html#sec-asynciteratorclose\n\n\t/** @type {AsyncIterator<T, TReturn>} */\n\t// @ts-ignore\n\tconst iterator = iterable[Symbol.asyncIterator]?.() ?? iterable[Symbol.iterator]?.();\n\n\tif (iterator === undefined) {\n\t\tthrow new TypeError(\'value is not async iterable\');\n\t}\n\n\t/** Whether the completion of the iterator was "normal", meaning it wasn\'t ended via `break` or a similar method */\n\tlet normal_completion = false;\n\ttry {\n\t\twhile (true) {\n\t\t\tconst { done, value } = (await track_reactivity_loss(iterator.next()))();\n\t\t\tif (done) {\n\t\t\t\tnormal_completion = true;\n\t\t\t\tbreak;\n\t\t\t}\n\t\t\tyield value;\n\t\t}\n\t} finally {\n\t\t// If the iterator had a normal completion and `return` is defined on the iterator, call it and return the value\n\t\tif (normal_completion && iterator.return !== undefined) {\n\t\t\t// eslint-disable-next-line no-unsafe-finally\n\t\t\treturn /** @type {TReturn} */ ((await track_reactivity_loss(iterator.return()))().value);\n\t\t}\n\t}\n}\n\nexport function unset_context(deactivate_batch = true) {\n\tset_active_effect(null);\n\tset_active_reaction(null);\n\tset_component_context(null);\n\tif (deactivate_batch) current_batch?.deactivate();\n\n\tif (DEV) {\n\t\tset_reactivity_loss_tracker(null);\n\t\tset_dev_stack(null);\n\t}\n}\n\n/**\n * @param {Array<() => void | Promise<void>>} thunks\n */\nexport function run(thunks) {\n\tconst restore = capture();\n\n\tconst decrement_pending = increment_pending();\n\n\tvar active = /** @type {Effect} */ (active_effect);\n\n\t/** @type {null | { error: any }} */\n\tvar errored = null;\n\n\t/** @param {any} error */\n\tconst handle_error = (error) => {\n\t\terrored = { error }; // wrap in object in case a promise rejects with a falsy value\n\n\t\tif (!aborted(active)) {\n\t\t\tinvoke_error_boundary(error, active);\n\t\t}\n\t};\n\n\tvar promise = Promise.resolve(thunks[0]()).catch(handle_error);\n\n\t/** @type {Blocker} */\n\tvar blocker = { promise, settled: false };\n\tvar blockers = [blocker];\n\n\tpromise.finally(() => {\n\t\tblocker.settled = true;\n\t\tunset_context();\n\t});\n\n\tfor (const fn of thunks.slice(1)) {\n\t\tpromise = promise\n\t\t\t.then(() => {\n\t\t\t\tif (errored) {\n\t\t\t\t\tthrow errored.error;\n\t\t\t\t}\n\n\t\t\t\tif (aborted(active)) {\n\t\t\t\t\tthrow STALE_REACTION;\n\t\t\t\t}\n\n\t\t\t\trestore();\n\t\t\t\treturn fn();\n\t\t\t})\n\t\t\t.catch(handle_error);\n\n\t\tconst blocker = { promise, settled: false };\n\t\tblockers.push(blocker);\n\n\t\tpromise.finally(() => {\n\t\t\tblocker.settled = true;\n\t\t\tunset_context();\n\t\t});\n\t}\n\n\tpromise\n\t\t// wait one more tick, so that template effects are\n\t\t// guaranteed to run before `$effect(...)`\n\t\t.then(() => Promise.resolve())\n\t\t.finally(() => decrement_pending());\n\n\treturn blockers;\n}\n\n/**\n * @param {Blocker[]} blockers\n */\nexport function wait(blockers) {\n\treturn Promise.all(blockers.map((b) => b.promise));\n}\n\n/**\n * @returns {(skip?: boolean) => void}\n */\nexport function increment_pending() {\n\tvar effect = /** @type {Effect} */ (active_effect);\n\tvar boundary = /** @type {Boundary} */ (effect.b);\n\tvar batch = /** @type {Batch} */ (current_batch);\n\tvar blocking = boundary.is_rendered();\n\n\tboundary.update_pending_count(1, batch);\n\tbatch.increment(blocking, effect);\n\n\treturn (skip = false) => {\n\t\tboundary.update_pending_count(-1, batch);\n\t\tbatch.decrement(blocking, effect, skip);\n\t};\n}\n',
            'packages/svelte/tests/runtime-runes/samples/async-reactivity-loss-for-await-break-return/_config.js': "import { tick } from 'svelte';\nimport { test } from '../../test';\nimport { normalise_trace_logs } from '../../../helpers.js';\n\nexport default test({\n\tcompileOptions: {\n\t\tdev: true\n\t},\n\thtml: '<p>pending</p>',\n\tasync test({ assert, target, warnings }) {\n\t\tawait tick();\n\n\t\tassert.htmlEqual(target.innerHTML, '<h1>number -> number -> number -> return -> ended</h1>');\n\n\t\tassert.deepEqual(normalise_trace_logs(warnings), [\n\t\t\t{\n\t\t\t\tlog: 'Detected reactivity loss when reading `values.length`. This happens when state is read in an async function after an earlier `await`'\n\t\t\t}\n\t\t]);\n\t}\n});\n",
            'packages/svelte/tests/runtime-runes/samples/async-reactivity-loss-for-await-break-return/main.svelte': "<script>\n\tlet values = $state([0, 1, 2]);\n\n\tasync function get_result() {\n\t\tconst logs = [];\n\n\t\tconst iterator = {\n\t\t\tindex: 0,\n\t\t\tasync next() {\n\t\t\t\tif (this.index >= values.length) return { done: true };\n\t\t\t\treturn { done: false, value: values[this.index++] };\n\t\t\t},\n\t\t\tasync return() {\n\t\t\t\tlogs.push('return');\n\t\t\t\treturn { done: true };\n\t\t\t},\n\t\t\t[Symbol.asyncIterator]() {\n\t\t\t\treturn this;\n\t\t\t}\n\t\t};\n\n\t\tfor await (const value of iterator) {\n\t\t\tlogs.push('number');\n\t\t\t// read reactive state after async iterator await\n\t\t\tif (values.length === 3 && value === 2) {\n\t\t\t\tbreak;\n\t\t\t}\n\t\t}\n\n\t\tlogs.push('ended');\n\t\treturn logs.join(' -> ');\n\t}\n</script>\n\n<svelte:boundary>\n\t<h1>{await get_result()}</h1>\n\n\t{#snippet pending()}\n\t\t<p>pending</p>\n\t{/snippet}\n</svelte:boundary>\n",
        }
