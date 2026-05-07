"""
Parameterized generator for GH419_angular_67033.

Source PR:    https://github.com/angular/angular/pull/67033
Source Issue: N/A

Seed varies: renames 'access' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH419_angular_67033'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH419_angular_67033'
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
                files[fpath] = files[fpath].replace('access', 'access' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH419_angular_67033',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'angular/angular',
                "pr_number": 67033,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/angular/angular/pull/67033",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'adev/src/content/guide/templates/ng-template.md': '# Create template fragments with ng-template\n\nInspired by the [native `<template>` element](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/template), the `<ng-template>` element lets you declare a **template fragment** – a section of content that you can dynamically or programmatically render.\n\n## Creating a template fragment\n\nYou can create a template fragment inside of any component template with the `<ng-template>` element:\n\n```angular-html\n<p>This is a normal element</p>\n\n<ng-template>\n  <p>This is a template fragment</p>\n</ng-template>\n```\n\nWhen the above is rendered, the content of the `<ng-template>` element is not rendered on the page. Instead, you can get a reference to the template fragment and write code to dynamically render it.\n\n### Binding context for fragments\n\nTemplate fragments may contain bindings with dynamic expressions:\n\n```angular-ts\n@Component({\n  /* ... */,\n  template: `<ng-template>You\'ve selected {{count}} items.</ng-template>`,\n})\nexport class ItemCounter {\n  count: number = 0;\n}\n```\n\nExpressions or statements in a template fragment are evaluated against the component in which the fragment is declared, regardless of where the fragment is rendered.\n\n## Getting a reference to a template fragment\n\nYou can get a reference to a template fragment in one of three ways:\n\n- By declaring a [template reference variable](/guide/templates/variables#template-reference-variables) on the `<ng-template>` element\n- By querying for the fragment with [a component or directive query](/guide/components/queries)\n- By injecting the fragment in a directive that\'s applied directly to an `<ng-template>` element.\n\nIn all three cases, the fragment is represented by a [TemplateRef](/api/core/TemplateRef) object.\n\n### Referencing a template fragment with a template reference variable\n\nYou can add a template reference variable to an `<ng-template>` element to reference that template fragment in other parts of the same template file:\n\n```angular-html\n<p>This is a normal element</p>\n\n<ng-template #myFragment>\n  <p>This is a template fragment</p>\n</ng-template>\n```\n\nYou can then reference this fragment anywhere else in the template via the `myFragment` variable.\n\n### Referencing a template fragment with queries\n\nYou can get a reference to a template fragment using any [component or directive query API](/guide/components/queries).\n\nYou can query the `TemplateRef` object directly using a `viewChild` query.\n\n```angular-ts\n@Component({\n  /* ... */,\n  template: `\n    <p>This is a normal element</p>\n\n    <ng-template>\n      <p>This is a template fragment</p>\n    </ng-template>\n  `,\n})\nexport class ComponentWithFragment {\n  templateRef = viewChild<TemplateRef<unknown>>(TemplateRef);\n}\n```\n\nYou can then reference this fragment in your component code or the component\'s template like any other class member.\n\nIf a template contains multiple fragments, you can assign a name to each fragment by adding a template reference variable to each `<ng-template>` element and querying for the fragments based on that name:\n\n```angular-ts\n@Component({\n  /* ... */,\n  template: `\n    <p>This is a normal element</p>\n\n    <ng-template #fragmentOne>\n      <p>This is one template fragment</p>\n    </ng-template>\n\n    <ng-template #fragmentTwo>\n      <p>This is another template fragment</p>\n    </ng-template>\n  `,\n})\nexport class ComponentWithFragment {\n    fragmentOne = viewChild<TemplateRef<unknown>>(\'fragmentOne\');\n    fragmentTwo = viewChild<TemplateRef<unknown>>(\'fragmentTwo\');\n}\n```\n\nAgain, you can then reference these fragments in your component code or the component\'s template like any other class members.\n\n### Injecting a template fragment\n\nA directive can inject a `TemplateRef` if that directive is applied directly to an `<ng-template>` element:\n\n```angular-ts\n@Directive({\n  selector: \'[myDirective]\',\n})\nexport class MyDirective {\n  private fragment = inject(TemplateRef);\n}\n```\n\n```angular-html\n<ng-template myDirective>\n  <p>This is one template fragment</p>\n</ng-template>\n```\n\nYou can then reference this fragment in your directive code like any other class member.\n\n## Rendering a template fragment\n\nOnce you have a reference to a template fragment\'s `TemplateRef` object, you can render a fragment in one of two ways: in your template with the `NgTemplateOutlet` directive or in your TypeScript code with `ViewContainerRef`.\n\n### Using `NgTemplateOutlet`\n\nThe `NgTemplateOutlet` directive from `@angular/common` accepts a `TemplateRef` and renders the fragment as a **sibling** to the element with the outlet. You should generally use `NgTemplateOutlet` on an [`<ng-container>` element](/guide/templates/ng-container).\n\nFirst, import `NgTemplateOutlet`:\n\n```typescript\nimport {NgTemplateOutlet} from \'@angular/common\';\n```\n\nThe following example declares a template fragment and renders that fragment to a `<ng-container>` element with `NgTemplateOutlet`:\n\n```angular-html\n<p>This is a normal element</p>\n\n<ng-template #myFragment>\n  <p>This is a fragment</p>\n</ng-template>\n\n<ng-container *ngTemplateOutlet="myFragment"></ng-container>\n```\n\nThis example produces the following rendered DOM:\n\n```angular-html\n<p>This is a normal element</p>\n<p>This is a fragment</p>\n```\n\n### Using `ViewContainerRef`\n\nA **view container** is a node in Angular\'s component tree that can contain content. Any component or directive can inject `ViewContainerRef` to get a reference to a view container corresponding to that component or directive\'s location in the DOM.\n\nYou can use the `createEmbeddedView` method on `ViewContainerRef` to dynamically render a template fragment. When you render a fragment with a `ViewContainerRef`, Angular appends it into the DOM as the next sibling of the component or directive that injected the `ViewContainerRef`.\n\nThe following example shows a component that accepts a reference to a template fragment as an input and renders that fragment into the DOM on a button click.\n\n```angular-ts\n@Component({\n  /* ... */,\n  selector: \'component-with-fragment\',\n  template: `\n    <h2>Component with a fragment</h2>\n    <ng-template #myFragment>\n      <p>This is the fragment</p>\n    </ng-template>\n    <my-outlet [fragment]="myFragment" />\n  `,\n})\nexport class ComponentWithFragment { }\n\n@Component({\n  /* ... */,\n  selector: \'my-outlet\',\n  template: `<button (click)="showFragment()">Show</button>`,\n})\nexport class MyOutlet {\n  private viewContainer = inject(ViewContainerRef);\n  fragment = input<TemplateRef<unknown> | undefined>();\n\n  showFragment() {\n    if (this.fragment()) {\n      this.viewContainer.createEmbeddedView(this.fragment());\n    }\n  }\n}\n```\n\nIn the example above, clicking the "Show" button results in the following output:\n\n```angular-html\n<component-with-fragment>\n  <h2>Component with a fragment>\n  <my-outlet>\n    <button>Show</button>\n  </my-outlet>\n  <p>This is the fragment</p>\n</component-with-fragment>\n```\n\n## Passing parameters when rendering a template fragment\n\nWhen declaring a template fragment with `<ng-template>`, you can additionally declare parameters accepted by the fragment. When you render a fragment, you can optionally pass a `context` object corresponding to these parameters. You can use data from this context object in binding expressions and statements, in addition to referencing data from the component in which the fragment is declared.\n\nEach parameter is written as an attribute prefixed with `let-` with a value matching a property name in the context object:\n\n```angular-html\n<ng-template let-pizzaTopping="topping">\n  <p>You selected: {{ pizzaTopping }}</p>\n</ng-template>\n```\n\n### Using `NgTemplateOutlet` {#using-ngtemplateoutlet-with-parameters}\n\nYou can bind a context object to the `ngTemplateOutletContext` input:\n\n```angular-html\n<ng-template #myFragment let-pizzaTopping="topping">\n  <p>You selected: {{ pizzaTopping }}</p>\n</ng-template>\n\n<ng-container [ngTemplateOutlet]="myFragment" [ngTemplateOutletContext]="{topping: \'onion\'}" />\n```\n\n### Using `ViewContainerRef` {#using-viewcontainerref-with-parameters}\n\nYou can pass a context object as the second argument to `createEmbeddedView`:\n\n```ts\nthis.viewContainer.createEmbeddedView(this.myFragment, {topping: \'onion\'});\n```\n\n## Structural directives\n\nA **structural directive** is any directive that:\n\n- Injects `TemplateRef`\n- Injects `ViewContainerRef` and programmatically renders the injected `TemplateRef`\n\nAngular supports a special convenience syntax for structural directives. If you apply the directive to an element and prefix the directive\'s selector with an asterisk (`*`) character, Angular interprets the entire element and all of its content as a template fragment:\n\n```angular-html\n<section *myDirective>\n  <p>This is a fragment</p>\n</section>\n```\n\nThis is equivalent to:\n\n```angular-html\n<ng-template myDirective>\n  <section>\n    <p>This is a fragment</p>\n  </section>\n</ng-template>\n```\n\nDevelopers typically use structural directives to conditionally render fragments or render fragments multiple times.\n\nFor more details, see [Structural Directives](/guide/directives/structural-directives).\n\n## Additional resources\n\nFor examples of how `ng-template` is used in other libraries, check out:\n\n- [Tabs from Angular Material](https://material.angular.dev/components/tabs/overview) - nothing gets rendered into the DOM until the tab is activated\n- [Table from Angular Material](https://material.angular.dev/components/table/overview) - allows developers to define different ways to render data\n',
        }
