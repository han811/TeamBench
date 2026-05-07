"""
Parameterized generator for GH806_consul_22817.

Source PR:    https://github.com/hashicorp/consul/pull/22817
Source Issue: N/A

Seed varies: renames 'bottom' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH806_consul_22817'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH806_consul_22817'
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
                files[fpath] = files[fpath].replace('bottom', 'bottom' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH806_consul_22817',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'hashicorp/consul',
                "pr_number": 22817,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/hashicorp/consul/pull/22817",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'ui/packages/consul-ui/app/components/popover-menu/menu-item/critical-button/index.hbs': "<Hds::Button\n  @color='critical'\n  @text={{@text}}\n  {{on 'click' @confirmAction}}\n  data-test-id='confirm-action'\n  data-test-delete\n/>",
            'ui/packages/consul-ui/app/modifiers/fix-code-block-aria.js': "import { modifier } from 'ember-modifier';\n\nexport default modifier(function fixCodeBlockAria(element) {\n  function fixAria() {\n    // Fix HDS CodeBlock ARIA issue - add role to pre elements with aria-labelledby\n    element.querySelectorAll('pre[aria-labelledby]:not([role])').forEach((pre) => {\n      pre.setAttribute('role', 'region');\n    });\n  }\n\n  setTimeout(fixAria, 100);\n  new MutationObserver(fixAria).observe(element, { childList: true, subtree: true });\n});\n",
            'ui/packages/consul-ui/app/modifiers/fix-super-select-aria.js': 'import { modifier } from \'ember-modifier\';\n\nexport default modifier(function fixSuperSelectAria(element) {\n  function fixAria() {\n    // Fix role="alert" → role="option" on select options\n    element.querySelectorAll(\'[role="alert"][aria-selected]\').forEach((el) => {\n      el.setAttribute(\'role\', \'option\');\n    });\n\n    // Remove invalid aria-controls and add missing aria-expanded\n    element.querySelectorAll(\'[aria-controls]\').forEach((el) => {\n      const controlsId = el.getAttribute(\'aria-controls\');\n      const dropdown = document.getElementById(controlsId);\n\n      if (!dropdown) {\n        el.removeAttribute(\'aria-controls\');\n        if (el.getAttribute(\'role\') === \'combobox\') {\n          el.setAttribute(\'aria-expanded\', \'false\');\n        }\n      } else if (el.getAttribute(\'role\') === \'combobox\' && !el.hasAttribute(\'aria-expanded\')) {\n        el.setAttribute(\'aria-expanded\', dropdown.offsetParent !== null ? \'true\' : \'false\');\n      }\n    });\n\n    // Add missing aria-label to listboxes\n    element.querySelectorAll(\'[role="listbox"]\').forEach((listbox) => {\n      if (!listbox.hasAttribute(\'aria-label\')) {\n        listbox.setAttribute(\'aria-label\', \'Available Options\');\n      }\n      // Make listbox keyboard accessible\n      if (!listbox.hasAttribute(\'tabindex\')) {\n        listbox.setAttribute(\'tabindex\', \'0\');\n      }\n    });\n  }\n\n  setTimeout(fixAria, 100);\n  new MutationObserver(fixAria).observe(element, { childList: true, subtree: true });\n});\n',
            'ui/packages/consul-ui/tests/integration/components/list-collection-test.js': '/**\n * Copyright (c) HashiCorp, Inc.\n * SPDX-License-Identifier: BUSL-1.1\n */\n\nimport { module, test } from \'qunit\';\nimport { setupRenderingTest } from \'ember-qunit\';\nimport { render, triggerEvent } from \'@ember/test-helpers\';\nimport hbs from \'htmlbars-inline-precompile\';\n\nmodule(\'Integration | Component | list collection\', function (hooks) {\n  setupRenderingTest(hooks);\n\n  test(\'it renders\', async function (assert) {\n    // Set any properties with this.set(\'myProperty\', \'value\');\n    // Handle any actions with this.on(\'myAction\', function(val) { ... });\n\n    await render(hbs`{{list-collection cell-layout=(fixed-grid-layout 800 50)}}`);\n\n    assert.dom(\'*\').hasText(\'\');\n\n    // Template block usage:\n    await render(hbs`\n      {{#list-collection cell-layout=(fixed-grid-layout 800 50)}}{{/list-collection}}\n    `);\n\n    assert.dom(\'*\').hasText(\'\');\n  });\n\n  test(\'it manages checked state and z-index on change\', async function (assert) {\n    this.set(\'items\', [\n      { id: 1, name: \'Item 1\' },\n      { id: 2, name: \'Item 2\' },\n    ]);\n\n    // Add a footer for collision detection\n    const footer = document.createElement(\'footer\');\n    footer.setAttribute(\'role\', \'contentinfo\');\n    footer.style.position = \'fixed\';\n    footer.style.bottom = \'0\';\n    footer.style.height = \'50px\';\n    document.body.appendChild(footer);\n\n    await render(hbs`\n      <ListCollection @items={{this.items}} as |item index Actions|>\n        <BlockSlot @name="header">{{item.name}}</BlockSlot>\n        <BlockSlot @name="actions" as |Actions|>\n          <Actions as |Action|>\n            <Action>\n              <BlockSlot @name="label">Action</BlockSlot>\n            </Action>\n          </Actions>\n        </BlockSlot>\n      </ListCollection>\n    `);\n\n    const checkbox = this.element.querySelector(\'input[type="checkbox"]\');\n    const row = this.element.querySelector(\'[data-test-list-row]\');\n\n    // Test checking - should set z-index and handle footer collision\n    checkbox.checked = true;\n    await triggerEvent(checkbox, \'change\');\n    assert.equal(row.style.zIndex, \'1\', \'Row should have z-index 1 when checked\');\n\n    // Test unchecking - should clear z-index\n    checkbox.checked = false;\n    await triggerEvent(checkbox, \'change\');\n    assert.strictEqual(row.style.zIndex, \'\', \'Row z-index should be cleared when unchecked\');\n\n    // Cleanup\n    document.body.removeChild(footer);\n  });\n});\n',
            'ui/packages/consul-ui/tests/integration/modifiers/fix-code-block-aria-test.js': 'import { module, test } from \'qunit\';\nimport { setupRenderingTest } from \'ember-qunit\';\nimport { render } from \'@ember/test-helpers\';\nimport hbs from \'htmlbars-inline-precompile\';\n\nfunction wait(ms) {\n  return new Promise((resolve) => setTimeout(resolve, ms));\n}\n\nmodule(\'Integration | Modifier | fix-code-block-aria\', function (hooks) {\n  setupRenderingTest(hooks);\n\n  test(\'it adds role="region" to pre elements with aria-labelledby\', async function (assert) {\n    await render(hbs`\n      <div {{fix-code-block-aria}}>\n        <pre aria-labelledby="title-123">\n          <code>console.log(\'hello\');</code>\n        </pre>\n      </div>\n    `);\n\n    await wait(150);\n    assert.dom(\'pre[aria-labelledby]\').hasAttribute(\'role\', \'region\');\n  });\n});\n',
            'ui/packages/consul-ui/tests/integration/modifiers/fix-super-select-aria-test.js': 'import { module, test } from \'qunit\';\nimport { setupRenderingTest } from \'ember-qunit\';\nimport { render } from \'@ember/test-helpers\';\nimport hbs from \'htmlbars-inline-precompile\';\n\nfunction wait(ms) {\n  return new Promise((resolve) => setTimeout(resolve, ms));\n}\n\nmodule(\'Integration | Modifier | fix-super-select-aria\', function (hooks) {\n  setupRenderingTest(hooks);\n\n  test(\'it changes role="alert" to role="option"\', async function (assert) {\n    await render(hbs`\n      <div {{fix-super-select-aria}}>\n        <span role="alert" aria-selected="true"></span>\n      </div>\n    `);\n    await wait(150); // Wait longer than the 100ms timeout\n    assert.dom(\'[role="option"][aria-selected]\').exists(\'role changed to option\');\n  });\n\n  test(\'it removes invalid aria-controls and adds aria-expanded\', async function (assert) {\n    await render(hbs`\n      <div {{fix-super-select-aria}}>\n        <span role="combobox" aria-controls="missing"></span>\n      </div>\n    `);\n    await wait(150);\n    assert.dom(\'[role="combobox"]\').doesNotHaveAttribute(\'aria-controls\', \'aria-controls removed\');\n    assert.dom(\'[role="combobox"]\').hasAttribute(\'aria-expanded\', \'false\', \'aria-expanded added\');\n  });\n\n  test(\'it adds missing aria-label to listboxes\', async function (assert) {\n    await render(hbs`\n      <div {{fix-super-select-aria}}>\n        <div role="listbox"></div>\n      </div>\n    `);\n    await wait(150);\n    assert\n      .dom(\'[role="listbox"]\')\n      .hasAttribute(\'aria-label\', \'Available Options\', \'aria-label added to listbox\');\n  });\n});\n',
        }
