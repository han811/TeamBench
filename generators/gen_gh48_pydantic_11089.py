"""
Parameterized generator for GH48_pydantic_11089.

Source PR:    https://github.com/pydantic/pydantic/pull/11089
Source Issue: https://github.com/pydantic/pydantic/issues/123

Seed varies: renames 'append' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH48_pydantic_11089'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH48_pydantic_11089'
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
                files[fpath] = files[fpath].replace('append', 'append' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH48_pydantic_11089',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'pydantic/pydantic',
                "pr_number": 11089,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/pydantic/pydantic/pull/11089",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'tests/test_types_self.py': 'import dataclasses\nimport re\nimport sys\nimport typing\nfrom typing import List, Optional, Type, Union\n\nimport pytest\nimport typing_extensions\nfrom typing_extensions import NamedTuple, TypedDict\n\nfrom pydantic import BaseModel, Field, PydanticUserError, TypeAdapter, ValidationError, computed_field, validate_call\n\n\n@pytest.fixture(\n    name=\'Self\',\n    params=[\n        pytest.param(typing, id=\'typing.Self\'),\n        pytest.param(typing_extensions, id=\'t_e.Self\'),\n    ],\n)\ndef fixture_self_all(request):\n    try:\n        return request.param.Self\n    except AttributeError:\n        pytest.skip(f\'Self is not available from {request.param}\')\n\n\ndef test_recursive_model(Self):\n    class SelfRef(BaseModel):\n        data: int\n        ref: typing.Optional[Self] = None\n\n    assert SelfRef(data=1, ref={\'data\': 2}).model_dump() == {\'data\': 1, \'ref\': {\'data\': 2, \'ref\': None}}\n\n\ndef test_recursive_model_invalid(Self):\n    class SelfRef(BaseModel):\n        data: int\n        ref: typing.Optional[Self] = None\n\n    with pytest.raises(\n        ValidationError,\n        match=r\'ref\\.ref\\s+Input should be a valid dictionary or instance of SelfRef \\[type=model_type,\',\n    ):\n        SelfRef(data=1, ref={\'data\': 2, \'ref\': 3}).model_dump()\n\n\ndef test_recursive_model_with_subclass(Self):\n    """Self refs should be valid and should reference the correct class in covariant direction"""\n\n    class SelfRef(BaseModel):\n        x: int\n        ref: Self | None = None\n\n    class SubSelfRef(SelfRef):\n        y: int\n\n    assert SubSelfRef(x=1, ref=SubSelfRef(x=3, y=4), y=2).model_dump() == {\n        \'x\': 1,\n        \'ref\': {\'x\': 3, \'ref\': None, \'y\': 4},  # SubSelfRef.ref: SubSelfRef\n        \'y\': 2,\n    }\n    assert SelfRef(x=1, ref=SubSelfRef(x=2, y=3)).model_dump() == {\n        \'x\': 1,\n        \'ref\': {\'x\': 2, \'ref\': None},\n    }  # SelfRef.ref: SelfRef\n\n\ndef test_recursive_model_with_subclass_invalid(Self):\n    """Self refs are invalid in contravariant direction"""\n\n    class SelfRef(BaseModel):\n        x: int\n        ref: Self | None = None\n\n    class SubSelfRef(SelfRef):\n        y: int\n\n    with pytest.raises(\n        ValidationError,\n        match=r\'ref\\s+Input should be a valid dictionary or instance of SubSelfRef \\[type=model_type,\',\n    ):\n        SubSelfRef(x=1, ref=SelfRef(x=2), y=3).model_dump()\n\n\ndef test_recursive_model_with_subclass_override(Self):\n    """Self refs should be overridable"""\n\n    class SelfRef(BaseModel):\n        x: int\n        ref: Self | None = None\n\n    class SubSelfRef(SelfRef):\n        y: int\n        ref: Optional[Union[SelfRef, Self]] = None\n\n    assert SubSelfRef(x=1, ref=SubSelfRef(x=3, y=4), y=2).model_dump() == {\n        \'x\': 1,\n        \'ref\': {\'x\': 3, \'ref\': None, \'y\': 4},\n        \'y\': 2,\n    }\n    assert SubSelfRef(x=1, ref=SelfRef(x=3, y=4), y=2).model_dump() == {\n        \'x\': 1,\n        \'ref\': {\'x\': 3, \'ref\': None},\n        \'y\': 2,\n    }\n\n\ndef test_self_type_with_field(Self):\n    class SelfRef(BaseModel):\n        x: int\n        refs: typing.List[Self] = Field(gt=0)\n\n    with pytest.raises(TypeError, match=re.escape("Unable to apply constraint \'gt\' to supplied value []")):\n        SelfRef(x=1, refs=[SelfRef(x=2, refs=[])])\n\n\ndef test_self_type_json_schema(Self):\n    class SelfRef(BaseModel):\n        x: int\n        refs: Optional[List[Self]] = []\n\n    assert SelfRef.model_json_schema() == {\n        \'$defs\': {\n            \'SelfRef\': {\n                \'properties\': {\n                    \'x\': {\'title\': \'X\', \'type\': \'integer\'},\n                    \'refs\': {\n                        \'anyOf\': [{\'items\': {\'$ref\': \'#/$defs/SelfRef\'}, \'type\': \'array\'}, {\'type\': \'null\'}],\n                        \'default\': [],\n                        \'title\': \'Refs\',\n                    },\n                },\n                \'required\': [\'x\'],\n                \'title\': \'SelfRef\',\n                \'type\': \'object\',\n            }\n        },\n        \'$ref\': \'#/$defs/SelfRef\',\n    }\n\n\ndef test_self_type_in_named_tuple(Self):\n    class SelfRefNamedTuple(NamedTuple):\n        x: int\n        ref: Self | None\n\n    ta = TypeAdapter(SelfRefNamedTuple)\n    assert ta.validate_python({\'x\': 1, \'ref\': {\'x\': 2, \'ref\': None}}) == (1, (2, None))\n\n\ndef test_self_type_in_typed_dict(Self):\n    class SelfRefTypedDict(TypedDict):\n        x: int\n        ref: Self | None\n\n    ta = TypeAdapter(SelfRefTypedDict)\n    assert ta.validate_python({\'x\': 1, \'ref\': {\'x\': 2, \'ref\': None}}) == {\'x\': 1, \'ref\': {\'x\': 2, \'ref\': None}}\n\n\ndef test_self_type_in_dataclass(Self):\n    @dataclasses.dataclass(frozen=True)\n    class SelfRef:\n        x: int\n        ref: Self | None\n\n    class Model(BaseModel):\n        item: SelfRef\n\n    m = Model.model_validate({\'item\': {\'x\': 1, \'ref\': {\'x\': 2, \'ref\': None}}})\n    assert m.item.x == 1\n    assert m.item.ref.x == 2\n    with pytest.raises(dataclasses.FrozenInstanceError):\n        m.item.ref.x = 3\n\n\ndef test_invalid_validate_call(Self):\n    with pytest.raises(PydanticUserError, match=\'`typing.Self` is invalid in this context\'):\n\n        @validate_call\n        def foo(self: Self):\n            pass\n\n\ndef test_invalid_validate_call_of_method(Self):\n    with pytest.raises(PydanticUserError, match=\'`typing.Self` is invalid in this context\'):\n\n        class A(BaseModel):\n            @validate_call\n            def foo(self: Self):\n                pass\n\n\ndef test_type_of_self(Self):\n    class A(BaseModel):\n        self_type: Type[Self]\n\n        @computed_field\n        def self_types1(self) -> List[Type[Self]]:\n            return [type(self), self.self_type]\n\n        # make sure forward refs are supported:\n        @computed_field\n        def self_types2(self) -> List[Type[\'Self\']]:\n            return [type(self), self.self_type]\n\n        @computed_field\n        def self_types3(self) -> \'List[Type[Self]]\':\n            return [type(self), self.self_type]\n\n        if sys.version_info >= (3, 9):\n            # standard container types are supported in 3.9+\n\n            @computed_field\n            def self_types4(self) -> \'list[type[Self]]\':\n                return [type(self), self.self_type]\n\n            @computed_field\n            def self_types5(self) -> list[\'type[Self]\']:\n                return [type(self), self.self_type]\n\n    class B(A): ...\n\n    A(self_type=A)\n    A(self_type=B)\n    B(self_type=B)\n\n    a = A(self_type=B)\n    for prop in (a.self_types1, a.self_types2, a.self_types3):\n        assert prop == [A, B]\n\n    for invalid_type in (type, int, A, object):\n        with pytest.raises(ValidationError) as exc_info:\n            B(self_type=invalid_type)\n\n        assert exc_info.value.errors(include_url=False) == [\n            {\n                \'type\': \'is_subclass_of\',\n                \'loc\': (\'self_type\',),\n                \'msg\': f\'Input should be a subclass of {B.__qualname__}\',\n                \'input\': invalid_type,\n                \'ctx\': {\'class\': B.__qualname__},\n            }\n        ]\n',
        }
