"""
Parameterized generator for GH290_attrs_1471.

Source PR:    https://github.com/python-attrs/attrs/pull/1471
Source Issue: N/A

Seed varies: renames 'allows' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH290_attrs_1471'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH290_attrs_1471'
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
                files[fpath] = files[fpath].replace('allows', 'allows' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH290_attrs_1471',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'python-attrs/attrs',
                "pr_number": 1471,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/python-attrs/attrs/pull/1471",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'src/attr/validators.pyi': 'from types import UnionType\nfrom typing import (\n    Any,\n    AnyStr,\n    Callable,\n    Container,\n    ContextManager,\n    Iterable,\n    Mapping,\n    Match,\n    Pattern,\n    TypeVar,\n    overload,\n)\n\nfrom attrs import _ValidatorType\nfrom attrs import _ValidatorArgType\n\n_T = TypeVar("_T")\n_T1 = TypeVar("_T1")\n_T2 = TypeVar("_T2")\n_T3 = TypeVar("_T3")\n_I = TypeVar("_I", bound=Iterable)\n_K = TypeVar("_K")\n_V = TypeVar("_V")\n_M = TypeVar("_M", bound=Mapping)\n\ndef set_disabled(run: bool) -> None: ...\ndef get_disabled() -> bool: ...\ndef disabled() -> ContextManager[None]: ...\n\n# To be more precise on instance_of use some overloads.\n# If there are more than 3 items in the tuple then we fall back to Any\n@overload\ndef instance_of(type: type[_T]) -> _ValidatorType[_T]: ...\n@overload\ndef instance_of(type: tuple[type[_T]]) -> _ValidatorType[_T]: ...\n@overload\ndef instance_of(\n    type: tuple[type[_T1], type[_T2]],\n) -> _ValidatorType[_T1 | _T2]: ...\n@overload\ndef instance_of(\n    type: tuple[type[_T1], type[_T2], type[_T3]],\n) -> _ValidatorType[_T1 | _T2 | _T3]: ...\n@overload\ndef instance_of(type: tuple[type, ...]) -> _ValidatorType[Any]: ...\n@overload\ndef instance_of(type: UnionType) -> _ValidatorType[Any]: ...\ndef optional(\n    validator: (\n        _ValidatorType[_T]\n        | list[_ValidatorType[_T]]\n        | tuple[_ValidatorType[_T]]\n    ),\n) -> _ValidatorType[_T | None]: ...\ndef in_(options: Container[_T]) -> _ValidatorType[_T]: ...\ndef and_(*validators: _ValidatorType[_T]) -> _ValidatorType[_T]: ...\ndef matches_re(\n    regex: Pattern[AnyStr] | AnyStr,\n    flags: int = ...,\n    func: Callable[[AnyStr, AnyStr, int], Match[AnyStr] | None] | None = ...,\n) -> _ValidatorType[AnyStr]: ...\ndef deep_iterable(\n    member_validator: _ValidatorArgType[_T],\n    iterable_validator: _ValidatorArgType[_I] | None = ...,\n) -> _ValidatorType[_I]: ...\n@overload\ndef deep_mapping(\n    key_validator: _ValidatorArgType[_K],\n    value_validator: _ValidatorArgType[_V] | None = ...,\n    mapping_validator: _ValidatorArgType[_M] | None = ...,\n) -> _ValidatorType[_M]: ...\n@overload\ndef deep_mapping(\n    key_validator: _ValidatorArgType[_K] | None = ...,\n    value_validator: _ValidatorArgType[_V] = ...,\n    mapping_validator: _ValidatorArgType[_M] | None = ...,\n) -> _ValidatorType[_M]: ...\ndef is_callable() -> _ValidatorType[_T]: ...\ndef lt(val: _T) -> _ValidatorType[_T]: ...\ndef le(val: _T) -> _ValidatorType[_T]: ...\ndef ge(val: _T) -> _ValidatorType[_T]: ...\ndef gt(val: _T) -> _ValidatorType[_T]: ...\ndef max_len(length: int) -> _ValidatorType[_T]: ...\ndef min_len(length: int) -> _ValidatorType[_T]: ...\ndef not_(\n    validator: _ValidatorType[_T],\n    *,\n    msg: str | None = None,\n    exc_types: type[Exception] | Iterable[type[Exception]] = ...,\n) -> _ValidatorType[_T]: ...\ndef or_(*validators: _ValidatorType[_T]) -> _ValidatorType[_T]: ...\n',
            'typing-examples/baseline_examples.py': '# SPDX-License-Identifier: MIT\n\n"""\nBaseline features that should be supported by all type checkers.\n"""\n\nfrom __future__ import annotations\n\nfrom typing import Any\n\nimport attrs\n\n\n@attrs.define(order=True)\nclass NGClass:\n    x: int = attrs.field(default=42)\n\n\nngc = NGClass(1)\n\n\n@attrs.mutable(slots=False)\nclass NGClass2:\n    x: int\n\n\nngc2 = NGClass2(1)\n\n\n@attrs.frozen(str=True)\nclass NGFrozen:\n    x: int\n\n\nngf = NGFrozen(1)\n\nattrs.fields(NGFrozen).x.evolve(eq=False)\na = attrs.fields(NGFrozen).x\na.evolve(repr=False)\n\n\n@attrs.define\nclass C:\n    a: int\n\n\nc = C(1)\nc.a\n\n\n@attrs.frozen\nclass D:\n    a: int\n\n\nD(1).a\n\n\n@attrs.define\nclass Derived(C):\n    b: int\n\n\nDerived(1, 2).a\nDerived(1, 2).b\n\n\n@attrs.define\nclass Error(Exception):\n    x: int\n\n\ntry:\n    raise Error(1)\nexcept Error as e:\n    e.x\n    e.args\n    str(e)\n\n\n@attrs.define\nclass AliasExample:\n    without_alias: int\n    _with_alias: int = attrs.field(alias="_with_alias")\n\n\nattrs.fields(AliasExample).without_alias.alias\nattrs.fields(AliasExample)._with_alias.alias\n\n\n@attrs.define\nclass Validated:\n    num: int = attrs.field(validator=attrs.validators.ge(0))\n\n\nattrs.validators.set_disabled(True)\nattrs.validators.set_disabled(False)\n\n\nwith attrs.validators.disabled():\n    Validated(num=-1)\n\n\n@attrs.define\nclass WithCustomRepr:\n    a: int = attrs.field(repr=True)\n    b: str = attrs.field(repr=False)\n    c: str = attrs.field(repr=lambda value: "c is for cookie")\n    d: bool = attrs.field(repr=str)\n\n\n@attrs.define(on_setattr=attrs.setters.validate)\nclass ValidatedSetter2:\n    a: int\n    b: str = attrs.field(on_setattr=attrs.setters.NO_OP)\n    c: bool = attrs.field(on_setattr=attrs.setters.frozen)\n    d: int = attrs.field(\n        on_setattr=[attrs.setters.convert, attrs.setters.validate]\n    )\n    e: bool = attrs.field(\n        on_setattr=attrs.setters.pipe(\n            attrs.setters.convert, attrs.setters.validate\n        )\n    )\n\n\n@attrs.define(eq=True, order=True)\nclass OrderFlags:\n    a: int = attrs.field(eq=False, order=False)\n    b: int = attrs.field(eq=True, order=True)\n\n\n# field_transformer\ndef ft_hook2(\n    cls: type, attribs: list[attrs.Attribute]\n) -> list[attrs.Attribute]:\n    return attribs\n\n\n@attrs.define(field_transformer=ft_hook2)\nclass TransformedAttrs2:\n    x: int\n\n\n@attrs.define\nclass FactoryTest:\n    a: list[int] = attrs.field(default=attrs.Factory(list))\n    b: list[Any] = attrs.field(default=attrs.Factory(list, False))\n    c: list[int] = attrs.field(default=attrs.Factory((lambda s: s.a), True))\n\n\nattrs.asdict(FactoryTest())\nattrs.asdict(FactoryTest(), retain_collection_types=False)\n\n\n@attrs.define(match_args=False)\nclass MatchArgs2:\n    a: int\n    b: int\n\n\n# NG versions of asdict/astuple\nattrs.asdict(MatchArgs2(1, 2))\nattrs.astuple(MatchArgs2(1, 2))\n\n\ndef accessing_from_attrs() -> None:\n    """\n    Use a function to keep the ns clean.\n    """\n    attrs.converters.optional\n    attrs.exceptions.FrozenError\n    attrs.filters.include\n    attrs.filters.exclude\n    attrs.setters.frozen\n    attrs.validators.and_\n    attrs.cmp_using\n',
        }
