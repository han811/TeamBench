"""
Parameterized generator for GH18_prisma_29009.

Source PR:    https://github.com/prisma/prisma/pull/29009
Source Issue: https://github.com/prisma/prisma/issues/29010

Seed varies: renames 'author' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH18_prisma_29009'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH18_prisma_29009'
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
                files[fpath] = files[fpath].replace('author', 'author' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH18_prisma_29009',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'prisma/prisma',
                "pr_number": 29009,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/prisma/prisma/pull/29009",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'packages/client/tests/functional/issues/29010-bigint-precision-relation-joins/_matrix.ts': "import { defineMatrix } from '../../_utils/defineMatrix'\nimport { Providers } from '../../_utils/providers'\n\nexport default defineMatrix(() => [\n  [{ provider: Providers.POSTGRESQL }, { provider: Providers.COCKROACHDB }, { provider: Providers.MYSQL }],\n])\n",
            'packages/client/tests/functional/issues/29010-bigint-precision-relation-joins/prisma/_schema.ts': 'import testMatrix from \'../_matrix\'\n\nexport default testMatrix.setupSchema(({ provider }) => {\n  return /* Prisma */ `\n  generator client {\n    provider = "prisma-client-js"\n    previewFeatures = ["relationJoins"]\n  }\n\n  datasource db {\n    provider = "${provider}"\n  }\n\n  model User {\n    id    BigInt  @id\n    name  String\n    posts Post[]\n  }\n\n  model Post {\n    id       BigInt  @id\n    title    String\n    authorId BigInt\n    author   User    @relation(fields: [authorId], references: [id])\n  }\n  `\n})\n',
            'packages/client/tests/functional/issues/29010-bigint-precision-relation-joins/tests.ts': "import testMatrix from './_matrix'\n// @ts-ignore\nimport type { PrismaClient } from './generated/prisma/client'\n\ndeclare let prisma: PrismaClient\n\n// BigInt IDs that exceed Number.MAX_SAFE_INTEGER (2^53 - 1 = 9007199254740991)\nconst USER_ID = BigInt('312590077454712834')\nconst POST_ID = BigInt('412590077454712834')\n\ntestMatrix.setupTestSuite(\n  () => {\n    beforeAll(async () => {\n      await prisma.post.deleteMany()\n      await prisma.user.deleteMany()\n\n      await prisma.user.create({\n        data: {\n          id: USER_ID,\n          name: 'Alice',\n          posts: {\n            create: {\n              id: POST_ID,\n              title: 'Hello World',\n            },\n          },\n        },\n      })\n    })\n\n    test('preserves BigInt precision in relationJoins queries', async () => {\n      const user = await prisma.user.findUnique({\n        where: { id: USER_ID },\n        relationLoadStrategy: 'join',\n        include: { posts: true },\n      })\n\n      expect(user).not.toBeNull()\n      expect(user!.id).toBe(USER_ID)\n      expect(user!.posts).toHaveLength(1)\n      expect(user!.posts[0].id).toBe(POST_ID)\n      expect(user!.posts[0].authorId).toBe(USER_ID)\n    })\n\n    test('preserves BigInt precision in nested relationJoins queries', async () => {\n      const post = await prisma.post.findUnique({\n        where: { id: POST_ID },\n        relationLoadStrategy: 'join',\n        include: {\n          author: {\n            include: { posts: true },\n          },\n        },\n      })\n\n      expect(post).not.toBeNull()\n      expect(post!.id).toBe(POST_ID)\n      expect(post!.authorId).toBe(USER_ID)\n      expect(post!.author.id).toBe(USER_ID)\n      expect(post!.author.posts).toHaveLength(1)\n      expect(post!.author.posts[0].id).toBe(POST_ID)\n    })\n  },\n  {\n    optOut: {\n      from: ['mongodb', 'sqlite', 'sqlserver'],\n      reason: 'relationJoins not supported',\n    },\n  },\n)\n",
        }
