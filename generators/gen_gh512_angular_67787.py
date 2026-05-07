"""
Parameterized generator for GH512_angular_67787.

Source PR:    https://github.com/angular/angular/pull/67787
Source Issue: N/A

Seed varies: renames 'aria' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH512_angular_67787'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH512_angular_67787'
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
                files[fpath] = files[fpath].replace('aria', 'aria' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH512_angular_67787',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'angular/angular',
                "pr_number": 67787,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/angular/angular/pull/67787",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'adev/shared-docs/pipeline/shared/marked/test/heading/heading.spec.mts': "/**\n * @license\n * Copyright Google LLC All Rights Reserved.\n *\n * Use of this source code is governed by an MIT-style license that can be\n * found in the LICENSE file at https://angular.dev/license\n */\n\nimport {readFile} from 'fs/promises';\nimport {JSDOM} from 'jsdom';\nimport {resolve} from 'node:path';\nimport {parseMarkdown} from '../../parse.mjs';\nimport {rendererContext} from '../renderer-context.mjs';\n\ndescribe('markdown to html', () => {\n  let markdownDocument: DocumentFragment;\n\n  beforeAll(async () => {\n    const markdownContent = await readFile(resolve('./heading.md'), {encoding: 'utf-8'});\n    markdownDocument = JSDOM.fragment(await parseMarkdown(markdownContent, rendererContext));\n  });\n\n  it('should treat # as document headers', () => {\n    const header = markdownDocument.querySelector('header');\n    expect(header?.classList.contains('docs-header')).toBeTrue();\n  });\n\n  it('should create a self referential link for non document headers', () => {\n    const h2 = markdownDocument.querySelector('h2');\n    const h2Anchor = h2?.firstElementChild;\n\n    const h2HeaderId = h2?.getAttribute('id');\n    const h2AnchorHref = h2Anchor?.getAttribute('href');\n\n    expect(h2HeaderId).toContain('headers-h2');\n    expect(h2AnchorHref).toBe(`#${h2HeaderId}`);\n  });\n\n  it('should make the docs anchors unreachable by tab', () => {\n    const docsAnchors = markdownDocument.querySelectorAll('.docs-anchor');\n    for (const anchor of docsAnchors) {\n      expect(anchor.getAttribute('tabindex')).toBe('-1');\n    }\n  });\n\n  // In case there is a valid usecase for duplicate header ids, we should use custom ids (as demonstrated below)\n  it('uses same id when multiple duplicate header names are found', () => {\n    const markdownDocument = JSDOM.fragment(\n      parseMarkdown(\n        `\n## Duplicate Anchor\n## Duplicate Anchor`,\n        rendererContext,\n      ),\n    );\n\n    const headers = markdownDocument.querySelectorAll('a.docs-anchor');\n    expect(headers[0].getAttribute('href')).toBe(headers[1].getAttribute('href'));\n  });\n\n  it('should remove code block markups', () => {\n    const markdownDocument = JSDOM.fragment(\n      parseMarkdown('## `myClass.myMethod` is the best', rendererContext),\n    );\n    const h2 = markdownDocument.querySelector('h2')!;\n    const h2Anchor = h2?.firstElementChild;\n\n    const h2HeaderId = h2?.getAttribute('id');\n    const h2AnchorHref = h2Anchor?.getAttribute('href');\n\n    expect(h2HeaderId).toContain('myclassmymethod-is-the-best');\n    expect(h2AnchorHref).toBe(`#${h2HeaderId}`);\n  });\n\n  it('should be able to extract non-ascii ids', () => {\n    const markdownDocument = JSDOM.fragment(\n      parseMarkdown(\n        '## ステップ 2 - アプリケーションのレイアウトに新しいコンポーネントを追加',\n        rendererContext,\n      ),\n    );\n    const h2 = markdownDocument.querySelector('h2')!;\n    const h2Anchor = h2?.firstElementChild;\n\n    const h2HeaderId = h2?.getAttribute('id');\n    const h2AnchorHref = h2Anchor?.getAttribute('href');\n\n    expect(h2HeaderId).toContain(\n      'ステップ-2---アプリケーションのレイアウトに新しいコンポーネントを追加',\n    );\n    expect(h2AnchorHref).toBe(`#${h2HeaderId}`);\n  });\n\n  it('should be able to extract custom ids', () => {\n    const markdownDocument = JSDOM.fragment(\n      parseMarkdown('## My heading {# my-custom-id }', rendererContext),\n    );\n\n    const h2 = markdownDocument.querySelector('h2')!;\n    const h2Anchor = h2?.firstElementChild;\n\n    const h2HeaderId = h2?.getAttribute('id');\n    const h2AnchorHref = h2Anchor?.getAttribute('href');\n\n    expect(h2HeaderId).toBe('my-custom-id');\n    expect(h2AnchorHref).toBe(`#${h2HeaderId}`);\n\n    // Verify that the custom ID syntax is removed from the displayed text\n    expect(h2Anchor?.textContent?.trim()).toBe('My heading');\n    expect(h2Anchor?.textContent).not.toContain('{#');\n  });\n\n  it('should be able to parse heading with a valid tag in a code block', () => {\n    const markdownDocument = JSDOM.fragment(\n      parseMarkdown('## Query for the `<h1>`', rendererContext),\n    );\n    const h2 = markdownDocument.querySelector('h2')!;\n\n    // The anchor element should be to only child\n    expect(h2.children.length).toBe(1);\n    expect(h2.firstElementChild?.tagName).toBe('A');\n\n    expect(h2.firstElementChild!.innerHTML).toBe('Query for the <code>&lt;h1&gt;</code>');\n  });\n\n  it('shoud now link symbols in headings', () => {\n    const markdownDocument = JSDOM.fragment(\n      parseMarkdown('## Hello **NEW** `Router` ', rendererContext),\n    );\n    const h2 = markdownDocument.querySelector('h2')!;\n\n    // The anchor element should be to only child, no nested anchor\n    expect(h2.children.length).toBe(1);\n\n    // We ensure that we still style the heading content\n    expect(markdownDocument.querySelector('strong')).toBeDefined();\n  });\n});\n",
            'adev/shared-docs/pipeline/shared/marked/transformations/heading.mts': '/*!\n * @license\n * Copyright Google LLC All Rights Reserved.\n *\n * Use of this source code is governed by an MIT-style license that can be\n * found in the LICENSE file at https://angular.dev/license\n */\n\nimport {Tokens} from \'marked\';\nimport {AdevDocsRenderer} from \'../renderer.mjs\';\nimport {getIdFromHeading} from \'../../heading.mjs\';\n\nexport function headingRender(\n  this: AdevDocsRenderer,\n  {depth, tokens, text: headingText, raw}: Tokens.Heading,\n): string {\n  this.context.disableAutoLinking = true;\n  const parsedText = this?.parser.parseInline(tokens, this);\n  this.context.disableAutoLinking = false;\n  if (depth === 1) {\n    return `\n    <header class="docs-header">\n      <docs-breadcrumb></docs-breadcrumb>\n      ${getPageTitle(parsedText, this.context.markdownFilePath)}\n    </header>\n    `;\n  }\n\n  const link = getIdFromHeading(headingText);\n\n  // Replace code backticks and remove custom ID syntax from the displayed label\n  let label = parsedText.replace(/`(.*?)`/g, \'<code>$1</code>\');\n  label = label.replace(/{#\\s*[\\w-]+\\s*}/g, \'\').trim();\n  const normalizedLabel = label.replace(/<\\/?code>/g, \'\');\n\n  return `\n  <h${depth} id="${link}">\n    <a href="#${link}" class="docs-anchor" tabindex="-1" aria-label="Link to ${normalizedLabel}">${label}</a>\n  </h${depth}>\n  `;\n}\n\n// TODO(josephperrott): Set edit content url based on the owner, repo and branch.\n\n/** The base url for editing the a file in the repository. */\nconst GITHUB_EDIT_CONTENT_URL = \'https://github.com/angular/angular/edit/main\';\n\n/** Get the page title with edit button to modify the page source. */\nexport function getPageTitle(text: string, filePath?: string): string {\n  return `\n  <!-- Page title -->\n  <div class="docs-page-title">\n    <h1 tabindex="-1">${text}</h1>\n    ${\n      filePath\n        ? `<a class="docs-github-links" target="_blank" href="${GITHUB_EDIT_CONTENT_URL}/${filePath}" title="Edit this page" aria-label="Edit this page">\n      <!-- Pencil -->\n      <docs-icon role="presentation">edit</docs-icon>\n    </a>`\n        : \'\'\n    }\n  </div>`;\n}\n',
        }
