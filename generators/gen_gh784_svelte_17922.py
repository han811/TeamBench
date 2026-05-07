"""
Parameterized generator for GH784_svelte_17922.

Source PR:    https://github.com/sveltejs/svelte/pull/17922
Source Issue: N/A

Seed varies: renames 'action' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH784_svelte_17922'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH784_svelte_17922'
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
                files[fpath] = files[fpath].replace('action', 'action' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH784_svelte_17922',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'sveltejs/svelte',
                "pr_number": 17922,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/sveltejs/svelte/pull/17922",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'packages/svelte/package.json': '{\n  "name": "svelte",\n  "description": "Cybernetically enhanced web apps",\n  "license": "MIT",\n  "version": "5.53.11",\n  "type": "module",\n  "types": "./types/index.d.ts",\n  "engines": {\n    "node": ">=18"\n  },\n  "files": [\n    "*.d.ts",\n    "src",\n    "!src/**/*.test.*",\n    "!src/**/*.d.ts",\n    "types",\n    "compiler",\n    "README.md"\n  ],\n  "module": "src/index-client.js",\n  "main": "src/index-client.js",\n  "exports": {\n    ".": {\n      "types": "./types/index.d.ts",\n      "worker": "./src/index-server.js",\n      "browser": "./src/index-client.js",\n      "default": "./src/index-server.js"\n    },\n    "./package.json": "./package.json",\n    "./action": {\n      "types": "./types/index.d.ts"\n    },\n    "./animate": {\n      "types": "./types/index.d.ts",\n      "default": "./src/animate/index.js"\n    },\n    "./attachments": {\n      "types": "./types/index.d.ts",\n      "default": "./src/attachments/index.js"\n    },\n    "./compiler": {\n      "types": "./types/index.d.ts",\n      "require": "./compiler/index.js",\n      "default": "./src/compiler/index.js"\n    },\n    "./easing": {\n      "types": "./types/index.d.ts",\n      "default": "./src/easing/index.js"\n    },\n    "./elements": {\n      "types": "./elements.d.ts"\n    },\n    "./internal": {\n      "default": "./src/internal/index.js"\n    },\n    "./internal/client": {\n      "default": "./src/internal/client/index.js"\n    },\n    "./internal/disclose-version": {\n      "default": "./src/internal/disclose-version.js"\n    },\n    "./internal/flags/async": {\n      "default": "./src/internal/flags/async.js"\n    },\n    "./internal/flags/legacy": {\n      "default": "./src/internal/flags/legacy.js"\n    },\n    "./internal/flags/tracing": {\n      "default": "./src/internal/flags/tracing.js"\n    },\n    "./internal/server": {\n      "default": "./src/internal/server/index.js"\n    },\n    "./legacy": {\n      "types": "./types/index.d.ts",\n      "worker": "./src/legacy/legacy-server.js",\n      "browser": "./src/legacy/legacy-client.js",\n      "default": "./src/legacy/legacy-server.js"\n    },\n    "./motion": {\n      "types": "./types/index.d.ts",\n      "default": "./src/motion/index.js"\n    },\n    "./reactivity": {\n      "types": "./types/index.d.ts",\n      "worker": "./src/reactivity/index-server.js",\n      "browser": "./src/reactivity/index-client.js",\n      "default": "./src/reactivity/index-server.js"\n    },\n    "./reactivity/window": {\n      "types": "./types/index.d.ts",\n      "default": "./src/reactivity/window/index.js"\n    },\n    "./server": {\n      "types": "./types/index.d.ts",\n      "default": "./src/server/index.js"\n    },\n    "./store": {\n      "types": "./types/index.d.ts",\n      "worker": "./src/store/index-server.js",\n      "browser": "./src/store/index-client.js",\n      "default": "./src/store/index-server.js"\n    },\n    "./transition": {\n      "types": "./types/index.d.ts",\n      "default": "./src/transition/index.js"\n    },\n    "./events": {\n      "types": "./types/index.d.ts",\n      "default": "./src/events/index.js"\n    }\n  },\n  "imports": {\n    "#client": "./src/internal/client/types.d.ts",\n    "#client/constants": "./src/internal/client/constants.js",\n    "#compiler": {\n      "types": "./src/compiler/private.d.ts",\n      "default": "./src/compiler/index.js"\n    },\n    "#compiler/builders": "./src/compiler/utils/builders.js",\n    "#server": "./src/internal/server/types.d.ts",\n    "#shared": "./src/internal/shared/types.d.ts"\n  },\n  "repository": {\n    "type": "git",\n    "url": "git+https://github.com/sveltejs/svelte.git",\n    "directory": "packages/svelte"\n  },\n  "bugs": {\n    "url": "https://github.com/sveltejs/svelte/issues"\n  },\n  "homepage": "https://svelte.dev",\n  "keywords": [\n    "svelte",\n    "UI",\n    "framework",\n    "templates",\n    "templating"\n  ],\n  "scripts": {\n    "build": "node scripts/process-messages && rollup -c && pnpm generate:types && node scripts/check-treeshakeability.js",\n    "dev": "node scripts/process-messages -w & rollup -cw",\n    "check": "tsc --project tsconfig.runtime.json && tsc && cd ./tests/types && tsc",\n    "check:tsgo": "tsgo --project tsconfig.runtime.json --skipLibCheck && tsgo --skipLibCheck",\n    "check:watch": "tsc --watch",\n    "generate:version": "node ./scripts/generate-version.js",\n    "generate:types": "node ./scripts/generate-types.js && tsc -p tsconfig.generated.json",\n    "prepublishOnly": "pnpm build",\n    "knip": "pnpm dlx knip"\n  },\n  "devDependencies": {\n    "@jridgewell/trace-mapping": "^0.3.25",\n    "@playwright/test": "^1.58.0",\n    "@rollup/plugin-commonjs": "^28.0.1",\n    "@rollup/plugin-node-resolve": "^15.3.0",\n    "@rollup/plugin-terser": "^0.4.4",\n    "@rollup/plugin-virtual": "^3.0.2",\n    "@types/aria-query": "^5.0.4",\n    "@types/node": "^20.11.5",\n    "dts-buddy": "^0.5.5",\n    "esbuild": "^0.25.10",\n    "rollup": "^4.59.0",\n    "source-map": "^0.7.4",\n    "tinyglobby": "^0.2.12",\n    "typescript": "^5.5.4",\n    "vitest": "^2.1.9"\n  },\n  "dependencies": {\n    "@jridgewell/remapping": "^2.3.4",\n    "@jridgewell/sourcemap-codec": "^1.5.0",\n    "@sveltejs/acorn-typescript": "^1.0.5",\n    "@types/estree": "^1.0.5",\n    "@types/trusted-types": "^2.0.7",\n    "acorn": "^8.12.1",\n    "aria-query": "5.3.1",\n    "axobject-query": "^4.1.0",\n    "clsx": "^2.1.1",\n    "devalue": "^5.6.4",\n    "esm-env": "^1.2.1",\n    "esrap": "^2.2.2",\n    "is-reference": "^3.0.3",\n    "locate-character": "^3.0.0",\n    "magic-string": "^0.30.11",\n    "zimmerframe": "^1.1.2"\n  }\n}\n',
        }
