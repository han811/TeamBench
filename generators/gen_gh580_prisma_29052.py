"""
Parameterized generator for GH580_prisma_29052.

Source PR:    https://github.com/prisma/prisma/pull/29052
Source Issue: N/A

Seed varies: renames 'abstract' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH580_prisma_29052'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH580_prisma_29052'
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
                files[fpath] = files[fpath].replace('abstract', 'abstract' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH580_prisma_29052',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'prisma/prisma',
                "pr_number": 29052,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/prisma/prisma/pull/29052",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'packages/client-runtime-utils/src/nullTypes.ts': "/**\n * Module-private symbol used to distinguish between instances of\n * `ObjectEnumValue` created inside and outside this module.\n */\nconst secret = Symbol()\n\n/**\n * Emulate a private property via a WeakMap manually. Using native private\n * properties is a breaking change for downstream users with minimal TypeScript\n * configs, because TypeScript uses ES3 as the default target.\n *\n * TODO: replace this with a `#representation` private property in the\n * `ObjectEnumValue` class and document minimal required `target` for TypeScript.\n */\nconst representations = new WeakMap<ObjectEnumValue, string>()\n\n/**\n * Base class for unique values of object-valued enums.\n */\nexport abstract class ObjectEnumValue {\n  constructor(arg?: symbol) {\n    if (arg === secret) {\n      representations.set(this, `Prisma.${this._getName()}`)\n    } else {\n      representations.set(this, `new Prisma.${this._getNamespace()}.${this._getName()}()`)\n    }\n  }\n\n  abstract _getNamespace(): string\n\n  _getName() {\n    return this.constructor.name\n  }\n\n  toString() {\n    return representations.get(this)!\n  }\n}\n\n/**\n * See helper in @internals package. Can not be used here\n * because importing internal breaks browser build.\n *\n * @param classObject\n * @param name\n */\nfunction setClassName(classObject: Function, name: string) {\n  Object.defineProperty(classObject, 'name', {\n    value: name,\n    configurable: true,\n  })\n}\n\nclass NullTypesEnumValue extends ObjectEnumValue {\n  override _getNamespace() {\n    return 'NullTypes'\n  }\n}\n\nexport class DbNullClass extends NullTypesEnumValue {\n  // Phantom private property to prevent structural type equality\n  // eslint-disable-next-line no-unused-private-class-members\n  readonly #_brand_DbNull!: void\n}\nsetClassName(DbNullClass, 'DbNull')\n\nexport class JsonNullClass extends NullTypesEnumValue {\n  // Phantom private property to prevent structural type equality\n  // eslint-disable-next-line no-unused-private-class-members\n  readonly #_brand_JsonNull!: void\n}\nsetClassName(JsonNullClass, 'JsonNull')\n\nexport class AnyNullClass extends NullTypesEnumValue {\n  // Phantom private property to prevent structural type equality\n  // eslint-disable-next-line no-unused-private-class-members\n  readonly #_brand_AnyNull!: void\n}\nsetClassName(AnyNullClass, 'AnyNull')\n\nexport const NullTypes = {\n  DbNull: DbNullClass,\n  JsonNull: JsonNullClass,\n  AnyNull: AnyNullClass,\n}\n\nexport const DbNull = new DbNullClass(secret)\nexport const JsonNull = new JsonNullClass(secret)\nexport const AnyNull = new AnyNullClass(secret)\n\n/**\n * Check if a value is the DBNull singleton instance.\n */\nexport function isDbNull(value: unknown): value is DbNullClass {\n  return value === DbNull\n}\n\n/**\n * Check if a value is the JsonNull singleton instance.\n */\nexport function isJsonNull(value: unknown): value is JsonNullClass {\n  return value === JsonNull\n}\n\n/**\n * Check if a value is the AnyNull singleton instance.\n */\nexport function isAnyNull(value: unknown): value is AnyNullClass {\n  return value === AnyNull\n}\n",
        }
