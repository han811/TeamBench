"""
Parameterized generator for GH450_angular_67783.

Source PR:    https://github.com/angular/angular/pull/67783
Source Issue: N/A

Seed varies: renames 'adding' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH450_angular_67783'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH450_angular_67783'
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
                files[fpath] = files[fpath].replace('adding', 'adding' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH450_angular_67783',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'angular/angular',
                "pr_number": 67783,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/angular/angular/pull/67783",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'modules/ssr-benchmarks/README.md': '## Intro\n\nThis small benchmark suite is dedicated to mesure & describe how compute time is spent when rendering an application like in SSR.\n\n## Struture\n\n- `./main.ts` is the entry point to run the benchmark\n- `./src` contains a sample app that exports a `render` function.\n- This app render a table of variable size, which depends on data (`initData()`)\n- This app is then rendered X numbers of times\n\n- Individual function calls are measured with `startMeasuring()`/`stopMeasuring()` from the core package.\n- If you add a new measure, make sure to add it also to the `levels` map for it to be represented correctly in the result\n\n## Build & run\n\n`pnpm bazel run //modules/ssr-benchmarks:run`\n\n### Running the benchmark in a browser environment\n\n`pnpm bazel run //modules/ssr-benchmarks:run_browser`\n\nThis bazel target will build the benchmark, start a http-server with a html that will load the benckmark script.\nThe benchmark script with this target will have DOM Emulation disabled.\nThe result will be visible in the devtools console.\n\nNote: Due to the CLI adding some polyfills, @angular/build is patched to disable DOM emulation and running server code inside a browser:\n\n1.  removing an import from `node:module` in `polyfills.server.mjs` (with `tail ...`)\n2.  removing the import of `platform-server/init`.\n\nTo run create a usable flame chart, prepare a narrowed run (like `benchmarkRun(10000, 20);`).\nThen in the performance tab of the devtools, trigger "Record & Reload" to generate a profile.\n\n### Deopt Explorer\n\nA target is dedicated to generate a v8 log that can be fed to the [Deopt Explorer extension](https://github.com/microsoft/deoptexplorer-vscode).\n\n1. Run `pnpm bazel run //modules/ssr-benchmarks:run_deopt`,\n2. open the project generated at the path after `Successfully ran all commands in test directory:`,\n3. open the logfile in the extension\n\n## Result example\n\n=== table with 10000 rows, with 1000 renders ===\n┌─────────┬──────────────────────────────────────┬──────────┬──────────┬────────────┬───────────┐\n│ (index) │ name │ min │ average │ percentage │ max │\n├─────────┼──────────────────────────────────────┼──────────┼──────────┼────────────┼───────────┤\n│ 0 │ \' renderApplication \' │ \'77.0ms\' │ \'86.4ms\' │ \'100.0%\' │ \'259.2ms\' │\n│ 1 │ \' └ createServerPlatform \' │ \'0.0ms\' │ \'0.1ms\' │ \'0.1%\' │ \'3.7ms\' │\n│ 2 │ \' └ bootstrap \' │ \'35.9ms\' │ \'42.6ms\' │ \'49.3%\' │ \'138.4ms\' │\n│ 3 │ \' └ \\_render \' │ \'39.7ms\' │ \'43.8ms\' │ \'50.7%\' │ \'124.9ms\' │\n│ 4 │ \' └ whenStable \' │ \'0.0ms\' │ \'0.0ms\' │ \'0.0%\' │ \'0.0ms\' │\n│ 5 │ \' └ prepareForHydration \' │ \'13.1ms\' │ \'14.8ms\' │ \'17.1%\' │ \'53.4ms\' │\n│ 6 │ \' └ insertEventRecordScript \' │ \'0.0ms\' │ \'0.0ms\' │ \'0.0%\' │ \'0.0ms\' │\n│ 7 │ \' └ serializeTransferStateFactory\' │ \'0.0ms\' │ \'0.0ms\' │ \'0.0%\' │ \'0.1ms\' │\n│ 8 │ \' └ renderToString \' │ \'7.3ms\' │ \'8.9ms\' │ \'10.3%\' │ \'41.8ms\' │\n└─────────┴──────────────────────────────────────┴──────────┴──────────┴────────────┴───────────┘\n\nNote: The max measure is often an outlier of the first few measures, probably before the JIT optimisation happens\n',
        }
