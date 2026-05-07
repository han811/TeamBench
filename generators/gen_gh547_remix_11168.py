"""
Parameterized generator for GH547_remix_11168.

Source PR:    https://github.com/remix-run/remix/pull/11168
Source Issue: N/A

Seed varies: renames 'action' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH547_remix_11168'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH547_remix_11168'
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
            task_id='GH547_remix_11168',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'remix-run/remix',
                "pr_number": 11168,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/remix-run/remix/pull/11168",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'packages/form-data-middleware/src/lib/form-data.test.ts': 'import * as assert from \'node:assert/strict\'\nimport { describe, it, mock } from \'node:test\'\n\nimport { FormDataParseError, type FileUploadHandler } from \'@remix-run/form-data-parser\'\nimport { createRouter } from \'@remix-run/fetch-router\'\n\nimport { formData } from \'./form-data.ts\'\n\ndescribe(\'formData middleware\', () => {\n  it(\'parses application/x-www-form-urlencoded form data from the request body\', async () => {\n    let router = createRouter({\n      middleware: [formData()],\n    })\n\n    router.post(\'/\', (context) => {\n      let entries = Object.fromEntries(context.get(FormData).entries())\n      return Response.json(entries)\n    })\n\n    let response = await router.fetch(\'https://remix.run/\', {\n      method: \'POST\',\n      headers: {\n        \'Content-Type\': \'application/x-www-form-urlencoded\',\n      },\n      body: \'name=test\',\n    })\n\n    assert.equal(response.status, 200)\n    assert.deepEqual(await response.json(), { name: \'test\' })\n  })\n\n  it(\'parses multipart/form-data form data from the request body\', async () => {\n    let router = createRouter({\n      middleware: [formData()],\n    })\n\n    router.post(\'/\', (context) => {\n      let entries = Object.fromEntries(context.get(FormData).entries())\n      return Response.json(entries)\n    })\n\n    let boundary = \'----WebKitFormBoundary1234567890\'\n    let response = await router.fetch(\'https://remix.run/\', {\n      method: \'POST\',\n      headers: {\n        \'Content-Type\': `multipart/form-data; boundary=${boundary}`,\n      },\n      body: [\n        `--${boundary}`,\n        \'Content-Disposition: form-data; name="name"\',\n        \'\',\n        \'test\',\n        `--${boundary}--`,\n      ].join(\'\\r\\n\'),\n    })\n\n    assert.equal(response.status, 200)\n    assert.deepEqual(await response.json(), { name: \'test\' })\n  })\n\n  it(\'stores uploaded files in context.get(FormData) on a multipart/form-data request\', async () => {\n    let router = createRouter({\n      middleware: [formData()],\n    })\n\n    router.post(\'/\', (context) => {\n      let file1 = context.get(FormData).get(\'file1\')\n      let file2 = context.get(FormData).get(\'file2\')\n\n      return Response.json({\n        file1: {\n          isFile: file1 instanceof File,\n          name: file1 instanceof File ? file1.name : null,\n          type: file1 instanceof File ? file1.type : null,\n        },\n        file2: {\n          isFile: file2 instanceof File,\n          name: file2 instanceof File ? file2.name : null,\n          type: file2 instanceof File ? file2.type : null,\n        },\n      })\n    })\n\n    let boundary = \'----WebKitFormBoundary1234567890\'\n    let response = await router.fetch(\'https://remix.run/\', {\n      method: \'POST\',\n      headers: {\n        \'Content-Type\': `multipart/form-data; boundary=${boundary}`,\n      },\n      body: [\n        `--${boundary}`,\n        \'Content-Disposition: form-data; name="file1"; filename="test1.txt"\',\n        \'Content-Type: text/plain\',\n        \'\',\n        \'test 1\',\n        `--${boundary}`,\n        \'Content-Disposition: form-data; name="file2"; filename="test2.txt"\',\n        \'Content-Type: text/plain\',\n        \'\',\n        \'test 2\',\n        `--${boundary}--`,\n      ].join(\'\\r\\n\'),\n    })\n\n    assert.equal(response.status, 200)\n    assert.deepEqual(await response.json(), {\n      file1: {\n        isFile: true,\n        name: \'test1.txt\',\n        type: \'text/plain\',\n      },\n      file2: {\n        isFile: true,\n        name: \'test2.txt\',\n        type: \'text/plain\',\n      },\n    })\n  })\n\n  it(\'throws when the request body is malformed multipart/form-data\', async () => {\n    let router = createRouter({\n      middleware: [formData()],\n    })\n\n    router.post(\'/\', (context) => Response.json(context.get(FormData)))\n\n    await assert.rejects(async () => {\n      await router.fetch(\'https://remix.run/\', {\n        method: \'POST\',\n        headers: {\n          \'Content-Type\': \'multipart/form-data\',\n        },\n        body: \'invalid\',\n      })\n    }, FormDataParseError)\n  })\n\n  it(\'suppresses parse errors when suppressErrors is true\', async () => {\n    let router = createRouter({\n      middleware: [formData({ suppressErrors: true })],\n    })\n\n    router.post(\'/\', (context) => {\n      let entries = Object.fromEntries(context.get(FormData).entries())\n      return Response.json(entries)\n    })\n\n    let response = await router.fetch(\'https://remix.run/\', {\n      method: \'POST\',\n      headers: {\n        \'Content-Type\': \'multipart/form-data\',\n      },\n      body: \'invalid\',\n    })\n\n    assert.equal(response.status, 200)\n    assert.deepEqual(await response.json(), {})\n  })\n\n  it(\'sets context.get(FormData) to an empty FormData when parse errors are suppressed\', async () => {\n    let router = createRouter({\n      middleware: [formData({ suppressErrors: true })],\n    })\n\n    router.post(\'/\', (context) =>\n      // Explicitly check that FormData exists in request context\n      Response.json({\n        isDefined: context.has(FormData),\n        isFormData: context.get(FormData) instanceof FormData,\n        isEmpty: context.get(FormData).entries().next().done,\n      }),\n    )\n\n    let response = await router.fetch(\'https://remix.run/\', {\n      method: \'POST\',\n      headers: {\n        \'Content-Type\': \'multipart/form-data\',\n      },\n      body: \'invalid\',\n    })\n\n    assert.equal(response.status, 200)\n    assert.deepEqual(await response.json(), {\n      isDefined: true,\n      isFormData: true,\n      isEmpty: true,\n    })\n  })\n\n  it(\'invokes a custom `uploadHandler` for file uploads\', async () => {\n    let uploadHandler = mock.fn<FileUploadHandler>()\n\n    let router = createRouter({\n      middleware: [formData({ uploadHandler })],\n    })\n\n    router.post(\'/\', () => new Response(\'home\'))\n\n    let boundary = \'----WebKitFormBoundary1234567890\'\n    let response = await router.fetch(\'https://remix.run/\', {\n      method: \'POST\',\n      headers: {\n        \'Content-Type\': `multipart/form-data; boundary=${boundary}`,\n      },\n      body: [\n        `--${boundary}`,\n        \'Content-Disposition: form-data; name="file1"; filename="test1.txt"\',\n        \'Content-Type: text/plain\',\n        \'\',\n        \'test 1\',\n        `--${boundary}`,\n        \'Content-Disposition: form-data; name="file2"; filename="test2.txt"\',\n        \'Content-Type: text/plain\',\n        \'\',\n        \'test 2\',\n        `--${boundary}--`,\n      ].join(\'\\r\\n\'),\n    })\n\n    assert.equal(response.status, 200)\n    assert.equal(await response.text(), \'home\')\n\n    assert.equal(uploadHandler.mock.calls.length, 2)\n\n    let call0 = uploadHandler.mock.calls[0]\n    let upload1 = call0.arguments[0]\n    assert.equal(upload1.fieldName, \'file1\')\n    assert.equal(upload1.name, \'test1.txt\')\n    assert.equal(upload1.type, \'text/plain\')\n    assert.equal(await upload1.text(), \'test 1\')\n\n    let call1 = uploadHandler.mock.calls[1]\n    let upload2 = call1.arguments[0]\n    assert.equal(upload2.fieldName, \'file2\')\n    assert.equal(upload2.name, \'test2.txt\')\n    assert.equal(upload2.type, \'text/plain\')\n    assert.equal(await upload2.text(), \'test 2\')\n  })\n})\n',
            'packages/form-data-middleware/src/lib/form-data.ts': "import {\n  FormDataParseError,\n  parseFormData,\n  type FileUploadHandler,\n  type ParseFormDataOptions,\n} from '@remix-run/form-data-parser'\nimport type { Middleware } from '@remix-run/fetch-router'\n\n/**\n * Options for the {@link formData} middleware.\n */\nexport interface FormDataOptions extends ParseFormDataOptions {\n  /**\n   * Set `true` to suppress parse errors.\n   *\n   * @default false\n   */\n  suppressErrors?: boolean\n  /**\n   * A function that handles file uploads. It receives a `FileUpload` object and may return any\n   * value that is a valid `FormData` value. Default is `undefined`, which means file uploads are\n   * stored in memory.\n   */\n  uploadHandler?: FileUploadHandler\n}\n\n/**\n * Middleware that parses `FormData` from the request body and populates request context.\n *\n * @param options Options for parsing form data\n * @returns A middleware function that parses form data\n */\nexport function formData(options?: FormDataOptions): Middleware {\n  let suppressErrors = options?.suppressErrors ?? false\n  let uploadHandler = options?.uploadHandler\n\n  return async (context) => {\n    if (context.method === 'GET' || context.method === 'HEAD') {\n      return\n    }\n\n    let contentType = context.headers.get('Content-Type')\n    if (\n      contentType == null ||\n      (!contentType.startsWith('multipart/') &&\n        !contentType.startsWith('application/x-www-form-urlencoded'))\n    ) {\n      context.set(FormData, new FormData())\n      return\n    }\n\n    try {\n      context.set(FormData, await parseFormData(context.request, options, uploadHandler))\n    } catch (error) {\n      if (!suppressErrors || !(error instanceof FormDataParseError)) {\n        throw error\n      }\n\n      context.set(FormData, new FormData())\n    }\n  }\n}\n",
        }
