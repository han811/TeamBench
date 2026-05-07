"""
Parameterized generator for GH310_hrm_4424.

Source PR:    https://github.com/arii/hrm/pull/4424
Source Issue: https://github.com/arii/hrm/issues/4403

Seed varies: renames 'adjusted' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH310_hrm_4424'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH310_hrm_4424'
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
                files[fpath] = files[fpath].replace('adjusted', 'adjusted' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH310_hrm_4424',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'arii/hrm',
                "pr_number": 4424,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/arii/hrm/pull/4424",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            '.env.example': '# .env.example\n# Copy this file to .env and fill in the values.\n\n# -- Next.js --\n# The environment your application is running in. (e.g. \'development\', \'production\')\nNODE_ENV=development\n\n# -- Server --\n# The port the server will run on.\nPORT=3000\n# The host the server will bind to.\nHOST=127.0.0.1\n\n# -- Authentication --\n# A secret key for NextAuth.js. Generate one with `openssl rand -hex 32`\nNEXTAUTH_SECRET=\n# The base URL of your application.\nNEXTAUTH_URL=http://127.0.0.1:3000\n# An alternative base URL of your application.\nBASE_URL=http://127.0.0.1:3000\n\n# -- Spotify API --\n# Your Spotify application\'s Client ID.\nSPOTIFY_CLIENT_ID=\n# Your Spotify application\'s Client Secret.\nSPOTIFY_CLIENT_SECRET=\n# The callback URL for Spotify authentication.\nSPOTIFY_CALLBACK_URL=http://127.0.0.1:3000/api/auth/callback/spotify\n\n# -- Internal API --\n# A secret for internal token delivery.\nINTERNAL_TOKEN_DELIVERY_SECRET=\n\n# -- Debugging --\n# Set to \'true\' or \'1\' to enable Spotify debugging.\nSPOTIFY_DEBUG=false\n\n# -- CI/CD --\n# Set to \'true\' in a CI environment.\nCI=false\n\n# -- Google Docs --\n# The URL of the public Google Doc to be parsed for workout data.\nGOOGLE_DOC_WORKOUT_URL="https://docs.google.com/document/d/e/2PACX-1vTev5AMiHYi2Jkg9x6zRQoiJ_o2X_wZMqAXVpwgjlSqzlcXelxSc7psjE8n3N-ghzXMFtnv51nc2fJZ/pub?embedded=true"\n# Feature Flag for Workout Table\nNEXT_PUBLIC_USE_NATIVE_TABLE=false\n\n# -- Client-side Configuration --\n# Optional: Override the default base URL for API requests. Defaults to the current origin. (e.g., \'https://your-api.com\', do NOT include \'/api\')\nNEXT_PUBLIC_API_URL=\n# Optional: Override the default base URL for WebSocket connections. Defaults to the current origin. (e.g., \'https://your-websocket-host.com\')\nNEXT_PUBLIC_WS_URL=\n\n# -- Rate Limiting --\n# The window in milliseconds for rate limiting.\nRATE_LIMIT_WINDOW_MS=60000\n# The maximum number of requests for the Spotify API.\nSPOTIFY_API_MAX_REQUESTS=30\n# The maximum number of requests for the internal API.\nINTERNAL_API_MAX_REQUESTS=100\n# The maximum number of requests for general API usage.\nGENERAL_API_MAX_REQUESTS=200\n\n# -- WebSocket --\n# The maximum number of WebSocket connections.\nWS_MAX_CONNECTIONS=5\n',
            'lib/env.ts': "import { z } from 'zod'\n\nconst envSchema = z.object({\n  NODE_ENV: z\n    .enum(['development', 'production', 'test'])\n    .default('development'),\n  PORT: z.coerce.number().default(3000),\n  HOST: z.string().default('0.0.0.0'),\n  NEXTAUTH_SECRET: z.string().min(1),\n  NEXTAUTH_URL: z.string().url(),\n  BASE_URL: z.string().url().optional(),\n  SPOTIFY_CLIENT_ID: z.string().min(1).optional(),\n  SPOTIFY_CLIENT_SECRET: z.string().min(1).optional(),\n  SPOTIFY_CALLBACK_URL: z.string().url().optional(),\n  INTERNAL_TOKEN_DELIVERY_SECRET: z.string().optional(),\n  SPOTIFY_DEBUG: z.string().optional(),\n  CI: z.string().optional(),\n  GOOGLE_DOC_WORKOUT_URL: z.string().url().optional(),\n  NEXT_PUBLIC_USE_NATIVE_TABLE: z.string().optional(),\n  NEXT_PUBLIC_API_URL: z.string().url().optional().or(z.literal('')),\n  NEXT_PUBLIC_WS_URL: z.string().url().optional().or(z.literal('')),\n  RATE_LIMIT_WINDOW_MS: z.coerce.number().default(60000),\n  SPOTIFY_API_MAX_REQUESTS: z.coerce.number().default(30),\n  INTERNAL_API_MAX_REQUESTS: z.coerce.number().default(100),\n  GENERAL_API_MAX_REQUESTS: z.coerce.number().default(200),\n  // The default of 1000 provides a generous limit for concurrent WebSocket connections,\n  // suitable for a moderate-scale deployment. This can be adjusted based on expected user load.\n  WS_MAX_CONNECTIONS: z.coerce.number().default(1000),\n  SPOTIFY_POLLING_INTERVAL_MS: z.coerce.number().default(5000),\n  SPOTIFY_DEVICE_POLLING_INTERVAL_MS: z.coerce.number().default(10000),\n  WEBSOCKET_GRACE_PERIOD_MS: z.coerce.number().default(5000),\n  WEBSOCKET_WATCHDOG_INTERVAL: z.coerce.number().optional(),\n  GEMINI_MODEL_FALLBACKS: z.string().optional(),\n  ANALYZE: z.string().optional(),\n  TESTING: z.string().optional(),\n  IS_DEPLOYMENT: z.string().optional(),\n  WS_URL: z.string().url().optional(),\n})\n\nconst parsedEnv = envSchema.safeParse(process.env)\n\nif (!parsedEnv.success) {\n  console.error('❌ Invalid environment variables:', parsedEnv.error.format())\n  throw parsedEnv.error\n}\n\nexport const env = parsedEnv.data\n",
            'tests/unit/lib/env.test.ts': "import { z } from 'zod'\n\ndescribe('Environment Variables', () => {\n  const OLD_ENV = process.env\n\n  beforeEach(() => {\n    jest.resetModules()\n    process.env = { ...OLD_ENV }\n  })\n\n  afterAll(() => {\n    process.env = OLD_ENV\n  })\n\n  it('should use default values for rate limiting and WebSocket connections', async () => {\n    process.env.NODE_ENV = 'test'\n    process.env.NEXTAUTH_URL = 'http://localhost:3000'\n    process.env.NEXTAUTH_SECRET = 'secret'\n    process.env.SPOTIFY_CLIENT_ID = 'id'\n    process.env.SPOTIFY_CLIENT_SECRET = 'secret'\n    const { env } = await import('../../../lib/env')\n    expect(env.RATE_LIMIT_WINDOW_MS).toBe(60000)\n    expect(env.SPOTIFY_API_MAX_REQUESTS).toBe(30)\n    expect(env.INTERNAL_API_MAX_REQUESTS).toBe(100)\n    expect(env.GENERAL_API_MAX_REQUESTS).toBe(200)\n    expect(env.WS_MAX_CONNECTIONS).toBe(1000)\n  })\n\n  it('should parse environment variables correctly', async () => {\n    process.env.NODE_ENV = 'test'\n    process.env.NEXTAUTH_URL = 'http://localhost:3000'\n    process.env.NEXTAUTH_SECRET = 'secret'\n    process.env.SPOTIFY_CLIENT_ID = 'id'\n    process.env.SPOTIFY_CLIENT_SECRET = 'secret'\n    process.env.RATE_LIMIT_WINDOW_MS = '120000'\n    process.env.SPOTIFY_API_MAX_REQUESTS = '60'\n    process.env.INTERNAL_API_MAX_REQUESTS = '200'\n    process.env.GENERAL_API_MAX_REQUESTS = '400'\n    process.env.WS_MAX_CONNECTIONS = '10'\n    const { env } = await import('../../../lib/env')\n    expect(env.RATE_LIMIT_WINDOW_MS).toBe(120000)\n    expect(env.SPOTIFY_API_MAX_REQUESTS).toBe(60)\n    expect(env.INTERNAL_API_MAX_REQUESTS).toBe(200)\n    expect(env.GENERAL_API_MAX_REQUESTS).toBe(400)\n    expect(env.WS_MAX_CONNECTIONS).toBe(10)\n  })\n\n  it('should throw an error for invalid environment variables', async () => {\n    process.env.NODE_ENV = 'test'\n    process.env.NEXTAUTH_URL = 'invalid-url'\n    process.env.NEXTAUTH_SECRET = 'secret'\n    process.env.SPOTIFY_CLIENT_ID = 'id'\n    process.env.SPOTIFY_CLIENT_SECRET = 'secret'\n    await expect(import('../../../lib/env')).rejects.toThrow(z.ZodError)\n  })\n})\n",
        }
