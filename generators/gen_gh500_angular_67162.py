"""
Parameterized generator for GH500_angular_67162.

Source PR:    https://github.com/angular/angular/pull/67162
Source Issue: N/A

Seed varies: renames 'about' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH500_angular_67162'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH500_angular_67162'
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
                files[fpath] = files[fpath].replace('about', 'about' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH500_angular_67162',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'angular/angular',
                "pr_number": 67162,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/angular/angular/pull/67162",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'adev/shared-docs/pipeline/shared/marked/extensions/docs-card/docs-card-container.mts': '/*!\n * @license\n * Copyright Google LLC All Rights Reserved.\n *\n * Use of this source code is governed by an MIT-style license that can be\n * found in the LICENSE file at https://angular.dev/license\n */\n\nimport {Tokens, Token, RendererThis, TokenizerThis} from \'marked\';\nimport {loadWorkspaceRelativeFile} from \'../../helpers.mjs\';\n\ninterface DocsCardContainerToken extends Tokens.Generic {\n  type: \'docs-card-container\';\n  cards: string;\n  headerTitle?: string;\n  headerImgSrc?: string;\n  header: Tokens.Heading;\n  tokens: Token[];\n}\n\n// Capture group 1: all attributes on the opening tag\n// Capture group 2: all content between the open and close tags\nconst cardContainerRule =\n  /^[^<]*<docs-card-container(?:\\s([^>]*))?>((?:.(?!\\/docs-card-container))*)<\\/docs-card-container>/s;\nconst headerTitleRule = /headerTitle="([^"]*)"/;\nconst headerImgSrcRule = /headerImgSrc="([^"]*)"/;\n\nexport const docsCardContainerExtension = {\n  name: \'docs-card-container\',\n  level: \'block\' as const,\n  start(src: string) {\n    return src.match(/^\\s*<docs-card-container/m)?.index;\n  },\n  tokenizer(this: TokenizerThis, src: string): DocsCardContainerToken | undefined {\n    const match = cardContainerRule.exec(src);\n\n    if (match) {\n      const attr = match[1] ? match[1].trim() : \'\';\n      const headerTitle = headerTitleRule.exec(attr);\n      const headerImgSrc = headerImgSrcRule.exec(attr);\n\n      const body = match[2].trim();\n      const header = headerTitle ? headerTitle[1] : \'\';\n\n      const token: DocsCardContainerToken = {\n        type: \'docs-card-container\',\n        raw: match[0],\n        cards: body ?? \'\',\n        headerImgSrc: headerImgSrc ? headerImgSrc[1] : undefined,\n        header: {\n          text: header,\n          raw: header,\n          tokens: this.lexer.inlineTokens(header, []),\n          type: \'heading\',\n          depth: 2,\n        },\n        tokens: [],\n      };\n      this.lexer.blockTokens(token.cards, token.tokens);\n      return token;\n    }\n    return undefined;\n  },\n  renderer(this: RendererThis, token: DocsCardContainerToken) {\n    return token.header.text\n      ? getContainerWithHeader(this, token)\n      : getStandardContainer(this, token);\n  },\n};\n\nfunction getStandardContainer(renderer: RendererThis, token: DocsCardContainerToken) {\n  return `\n    <div class="docs-card-grid">\n      ${renderer.parser.parse(token.tokens)}\n    </div>\n    `;\n}\n\nfunction getContainerWithHeader(renderer: RendererThis, token: DocsCardContainerToken) {\n  // We can assume that all illustrations are svg files\n  // We need to read svg content, instead of renering svg with `img`,\n  // cause we would like to use CSS variables to support dark and light mode.\n  let illustration = token.headerImgSrc ? loadWorkspaceRelativeFile(token.headerImgSrc!) : \'\';\n\n  return `\n    <div class="docs-card-container-wrapper">\n      <div class="docs-card-container-header">\n        ${renderer.parser.renderer.heading(token.header)}\n          <span class="header-img">${illustration}</span>\n      </div>\n      <div class="docs-card-container-content docs-card-grid">\n        ${renderer.parser.parse(token.tokens)}\n      </div>\n    </div>\n    `;\n}\n',
            'adev/shared-docs/pipeline/shared/marked/extensions/docs-card/docs-card.mts': '/*!\n * @license\n * Copyright Google LLC All Rights Reserved.\n *\n * Use of this source code is governed by an MIT-style license that can be\n * found in the LICENSE file at https://angular.dev/license\n */\n\nimport {RendererThis, Token, TokenizerThis, Tokens} from \'marked\';\nimport {anchorTarget, loadWorkspaceRelativeFile} from \'../../helpers.mjs\';\nimport {AdevDocsRenderer} from \'../../renderer.mjs\';\n\ninterface DocsCardToken extends Tokens.Generic {\n  type: \'docs-card\';\n  title: string;\n  body: string;\n  link?: string;\n  href?: string;\n  imgSrc?: string;\n  iconImgSrc?: string; // Need image since icons are custom\n  tokens: Token[];\n}\n\n// Capture group 1: all attributes on the opening tag\n// Capture group 2: all content between the open and close tags\nconst cardRule = /^[^<]*<docs-card(?:\\s([^>]*))?>((?:.(?!\\/docs-card))*)<\\/docs-card>/s;\n\nconst titleRule = /title="([^"]*)"/;\nconst linkRule = /link="([^"]*)"/;\nconst hrefRule = /href="([^"]*)"/;\nconst imgSrcRule = /imgSrc="([^"]*)"/;\nconst iconImgSrcRule = /iconImgSrc="([^"]*)"/;\n\nexport const docsCardExtension = {\n  name: \'docs-card\',\n  level: \'block\' as const,\n  start(src: string) {\n    return src.match(/^\\s*<docs-card\\s*/m)?.index;\n  },\n  tokenizer(this: TokenizerThis, src: string): DocsCardToken | undefined {\n    const match = cardRule.exec(src);\n\n    if (match) {\n      const attr = match[1] ? match[1].trim() : \'\';\n      const title = titleRule.exec(attr);\n      const link = linkRule.exec(attr);\n      const href = hrefRule.exec(attr);\n      const imgSrc = imgSrcRule.exec(attr);\n      const iconImgSrc = iconImgSrcRule.exec(attr);\n\n      const body = match[2].trim();\n\n      const token: DocsCardToken = {\n        type: \'docs-card\',\n        raw: match[0],\n        title: title ? title[1] : \'\',\n        body: body ?? \'\',\n        href: href ? href[1] : undefined,\n        link: link ? link[1] : undefined,\n        imgSrc: imgSrc ? imgSrc[1] : undefined,\n        iconImgSrc: iconImgSrc ? iconImgSrc[1] : undefined,\n        tokens: [],\n      };\n      this.lexer.blockTokens(token.body, token.tokens);\n      return token;\n    }\n    return undefined;\n  },\n  renderer(this: RendererThis, token: DocsCardToken) {\n    return token.imgSrc\n      ? getCardWithSvgIllustration(this, token)\n      : getStandardCard(this.parser.renderer as AdevDocsRenderer, token);\n  },\n};\n\nfunction getStandardCard(renderer: AdevDocsRenderer, token: DocsCardToken) {\n  if (token.iconImgSrc && token.href) {\n    // We can assume that all icons are svg files since they are custom.\n    // We need to read svg content, instead of renering svg with `img`,\n    // cause we would like to use CSS variables to support dark and light mode.\n    const icon = loadWorkspaceRelativeFile(token.iconImgSrc);\n\n    return `\n    <a href="${token.href}" ${anchorTarget(token.href)} class="docs-card">\n      <div>\n        ${icon}\n        <h3>${token.title}</h3>\n        ${renderer.parser.parse(token.tokens)}\n      </div>\n      <span>${token.link ? token.link : \'Learn more\'}</span>\n    </a>\n    `;\n  } else if (token.href) {\n    return `\n    <a href="${token.href}" ${anchorTarget(token.href)} class="docs-card">\n      <div>\n        ${token.title ? `<h3>${token.title}</h3>` : \'\'}\n        ${parseWithoutCreatingLinks(renderer, token)}\n      </div>\n      <span>${token.link ? token.link : \'Learn more\'}</span>\n    </a>\n    `;\n  }\n  return `\n  <div class="docs-card">\n    <div>\n      ${token.title ? `<h3>${token.title}</h3>` : \'\'}\n      ${renderer.parser.parse(token.tokens)}\n    </div>\n    ${token.link ? `<span>${token.link}</span>` : \'\'}\n  </div>\n  `;\n}\n\nfunction parseWithoutCreatingLinks(renderer: AdevDocsRenderer, token: DocsCardToken) {\n  renderer.context.disableAutoLinking = true;\n  const parsed = renderer.parser.parse(token.tokens);\n  renderer.context.disableAutoLinking = false;\n  return parsed;\n}\n\nfunction getCardWithSvgIllustration(renderer: RendererThis, token: DocsCardToken) {\n  // We can assume that all illustrations are svg files\n  // We need to read svg content, instead of renering svg with `img`,\n  // cause we would like to use CSS variables to support dark and light mode.\n  const illustration = loadWorkspaceRelativeFile(token.imgSrc!);\n\n  if (token.href) {\n    return `\n      <a href="${token.href}" ${anchorTarget(token.href)} class="docs-card docs-card-with-svg">\n        ${illustration}\n        <div class="docs-card-text-content">\n          <div>\n            ${token.title ? `<h3>${token.title}</h3>` : \'\'}\n            ${renderer.parser.parse(token.tokens)}\n          </div>\n          <span>${token.link ? token.link : \'Learn more\'}</span>\n        </div>\n      </a>\n      `;\n  }\n  return `\n    <div class="docs-card docs-card-with-svg">\n      ${illustration}\n      <div class="docs-card-text-content">\n      ${token.title ? `<h3>${token.title}</h3>` : \'\'}\n      ${renderer.parser.parse(token.tokens)}\n      </div>\n    </div>\n    `;\n}\n',
            'adev/shared-docs/pipeline/shared/marked/test/docs-card-container/docs-card-container.md': '<docs-card-container>\n  <docs-card></docs-card>\n  <docs-card></docs-card>\n</docs-card-container>\n',
            'adev/shared-docs/pipeline/shared/marked/test/docs-card-container/docs-card-container.spec.mts': "/**\n * @license\n * Copyright Google LLC All Rights Reserved.\n *\n * Use of this source code is governed by an MIT-style license that can be\n * found in the LICENSE file at https://angular.dev/license\n */\n\nimport {parseMarkdown} from '../../parse.mjs';\nimport {resolve} from 'node:path';\nimport {readFile} from 'fs/promises';\nimport {JSDOM} from 'jsdom';\nimport {rendererContext} from '../renderer-context.mjs';\n\ndescribe('markdown to html', () => {\n  let markdownDocument: DocumentFragment;\n\n  beforeAll(async () => {\n    const markdownContent = await readFile(resolve('docs-card-container.md'), {encoding: 'utf-8'});\n    markdownDocument = JSDOM.fragment(await parseMarkdown(markdownContent, rendererContext));\n  });\n\n  it('creates card containers containing multiple cards', () => {\n    const containerEl = markdownDocument.querySelector('.docs-card-grid');\n\n    expect(containerEl!.children.length).toBe(2);\n    expect(containerEl!.classList.contains('docs-card-grid')).toBeTrue();\n  });\n});\n",
        }
