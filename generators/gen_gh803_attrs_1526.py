"""
Parameterized generator for GH803_attrs_1526.

Source PR:    https://github.com/python-attrs/attrs/pull/1526
Source Issue: N/A

Seed varies: renames 'a_number' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH803_attrs_1526'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH803_attrs_1526'
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
                files[fpath] = files[fpath].replace('a_number', 'a_number' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH803_attrs_1526',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'python-attrs/attrs',
                "pr_number": 1526,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/python-attrs/attrs/pull/1526",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'docs/types.md': '# Type Annotations\n\n*attrs* comes with first-class support for type annotations for both {pep}`526` and legacy syntax.\n\nHowever, they will remain *optional* forever, therefore the example from the README could also be written as:\n\n```{doctest}\n>>> from attrs import define, field\n\n>>> @define\n... class SomeClass:\n...     a_number = field(default=42)\n...     list_of_numbers = field(factory=list)\n\n>>> sc = SomeClass(1, [1, 2, 3])\n>>> sc\nSomeClass(a_number=1, list_of_numbers=[1, 2, 3])\n```\n\nYou can choose freely between the approaches, but please remember that if you choose to use type annotations, you **must** annotate **all** attributes!\n\n:::{caution}\nIf you define a class with a {func}`attrs.field` that **lacks** a type annotation, *attrs* will **ignore** other fields that have a type annotation, but are not defined using {func}`attrs.field`:\n\n```{doctest}\n>>> @define\n... class SomeClass:\n...     a_number = field(default=42)\n...     another_number: int = 23\n>>> SomeClass()\nSomeClass(a_number=42)\n```\n:::\n\nEven when going all-in on type annotations, you will need {func}`attrs.field` for some advanced features, though.\n\nOne of those features are the decorator-based features like defaults.\nIt\'s important to remember that *attrs* doesn\'t do any magic behind your back.\nAll the decorators are implemented using an object that is returned by the call to {func}`attrs.field`.\n\nAttributes that only carry a class annotation do not have that object so trying to call a method on it will inevitably fail.\n\n---\n\nPlease note that types -- regardless how added -- are *only metadata* that can be queried from the class and they aren\'t used for anything out of the box!\n\nBecause Python does not allow references to a class object before the class is defined,\ntypes may be defined as string literals, so-called *forward references* ({pep}`526`).\nYou can enable this automatically for a whole module by using `from __future__ import annotations` ({pep}`563`).\nIn this case *attrs* simply puts these string literals into the `type` attributes.\nIf you need to resolve these to real types, you can call {func}`attrs.resolve_types` which will update the attribute in place.\n\nIn practice though, types show their biggest usefulness in combination with tools like [Mypy], [*pytype*], or [Pyright] that have dedicated support for *attrs* classes.\n\nThe addition of static types is certainly one of the most exciting features in the Python ecosystem and helps you write *correct* and *verified self-documenting* code.\n\n\n## Mypy\n\nWhile having a nice syntax for type metadata is great, it\'s even greater that [Mypy] ships with a dedicated *attrs* plugin which allows you to statically check your code.\n\nImagine you add another line that tries to instantiate the defined class using `SomeClass("23")`.\nMypy will catch that error for you:\n\n```console\n$ mypy t.py\nt.py:12: error: Argument 1 to "SomeClass" has incompatible type "str"; expected "int"\n```\n\nThis happens *without* running your code!\n\nAnd it also works with *both* legacy annotation styles.\nTo Mypy, this code is equivalent to the one above:\n\n```python\n@attr.s\nclass SomeClass:\n    a_number = attr.ib(default=42)  # type: int\n    list_of_numbers = attr.ib(factory=list, type=list[int])\n```\n\nThe approach used for `list_of_numbers` one is only a available in our [old-style API](names.md) which is why the example still uses it.\n\n\n## Pyright\n\n*attrs* provides support for [Pyright] through the `dataclass_transform` / {pep}`681` specification.\nThis provides static type inference for a subset of *attrs* equivalent to standard-library {mod}`dataclasses`,\nand requires explicit type annotations using the {func}`attrs.define` or `@attr.s(auto_attribs=True)` API.\n\nGiven the following definition, Pyright will generate static type signatures for `SomeClass` attribute access, `__init__`, `__eq__`, and comparison methods:\n\n```\n@attrs.define\nclass SomeClass:\n    a_number: int = 42\n    list_of_numbers: list[int] = attr.field(factory=list)\n```\n\n:::{warning}\nThe Pyright inferred types are a tiny subset of those supported by Mypy, including:\n\n- The `attrs.frozen` decorator is not typed with frozen attributes, which are properly typed via `attrs.define(frozen=True)`.\n\nYour constructive feedback is welcome in both [attrs#795](https://github.com/python-attrs/attrs/issues/795) and [pyright#1782](https://github.com/microsoft/pyright/discussions/1782).\nGenerally speaking, the decision on improving *attrs* support in Pyright is entirely Microsoft\'s prerogative and they unequivocally indicated that they\'ll only add support for features that go through the PEP process, though.\n:::\n\n\n## Class variables and constants\n\nIf you are adding type annotations to all of your code, you might wonder how to define a class variable (as opposed to an instance variable), because a value assigned at class scope becomes a default for that attribute.\nThe proper way to type such a class variable, though, is with {data}`typing.ClassVar`, which indicates that the variable should only be assigned in the class (or its subclasses) and not in instances of the class.\n*attrs* will skip over members annotated with {data}`typing.ClassVar`, allowing you to write a type annotation without turning the member into an attribute.\nClass variables are often used for constants, though they can also be used for mutable singleton data shared across all instances of the class.\n\n```\n@attrs.define\nclass PngHeader:\n    SIGNATURE: typing.ClassVar[bytes] = b\'\\x89PNG\\r\\n\\x1a\\n\'\n    height: int\n    width: int\n    interlaced: int = 0\n    ...\n```\n\n[Mypy]: http://mypy-lang.org\n[Pyright]: https://github.com/microsoft/pyright\n[*pytype*]: https://google.github.io/pytype/\n',
        }
