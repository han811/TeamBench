"""
Parameterized generator for GH829_attrs_1489.

Source PR:    https://github.com/python-attrs/attrs/pull/1489
Source Issue: N/A

Seed varies: renames 'access' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH829_attrs_1489'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH829_attrs_1489'
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
            task_id='GH829_attrs_1489',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'python-attrs/attrs',
                "pr_number": 1489,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/python-attrs/attrs/pull/1489",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'bench/test_benchmarks.py': '"""\nBenchmark attrs using CodSpeed.\n"""\n\nfrom __future__ import annotations\n\nimport pytest\n\nimport attrs\n\n\npytestmark = pytest.mark.benchmark()\n\nROUNDS = 1_000\n\n\ndef test_create_simple_class():\n    """\n    Benchmark creating  a simple class without any extras.\n    """\n    for _ in range(ROUNDS):\n\n        @attrs.define\n        class LocalC:\n            x: int\n            y: str\n            z: dict[str, int]\n\n\ndef test_create_frozen_class():\n    """\n    Benchmark creating a frozen class without any extras.\n    """\n    for _ in range(ROUNDS):\n\n        @attrs.frozen\n        class LocalC:\n            x: int\n            y: str\n            z: dict[str, int]\n\n        LocalC(1, "2", {})\n\n\ndef test_create_simple_class_make_class():\n    """\n    Benchmark creating a simple class using attrs.make_class().\n    """\n    for i in range(ROUNDS):\n        LocalC = attrs.make_class(\n            f"LocalC{i}",\n            {\n                "x": attrs.field(type=int),\n                "y": attrs.field(type=str),\n                "z": attrs.field(type=dict[str, int]),\n            },\n        )\n\n        LocalC(1, "2", {})\n\n\n@attrs.define\nclass C:\n    x: int = 0\n    y: str = "foo"\n    z: dict[str, int] = attrs.Factory(dict)\n\n\ndef test_instantiate_no_defaults():\n    """\n    Benchmark instantiating a class without using any defaults.\n    """\n    for _ in range(ROUNDS):\n        C(1, "2", {})\n\n\ndef test_instantiate_with_defaults():\n    """\n    Benchmark instantiating a class relying on defaults.\n    """\n    for _ in range(ROUNDS):\n        C()\n\n\ndef test_eq_equal():\n    """\n    Benchmark comparing two equal instances for equality.\n    """\n    c1 = C()\n    c2 = C()\n\n    for _ in range(ROUNDS):\n        c1 == c2\n\n\ndef test_eq_unequal():\n    """\n    Benchmark comparing two unequal instances for equality.\n    """\n    c1 = C()\n    c2 = C(1, "bar", {"baz": 42})\n\n    for _ in range(ROUNDS):\n        c1 == c2\n\n\n@attrs.frozen\nclass HashableC:\n    x: int = 0\n    y: str = "foo"\n    z: tuple[str] = ("bar",)\n\n\ndef test_hash():\n    """\n    Benchmark hashing an instance.\n    """\n    c = HashableC()\n\n    for _ in range(ROUNDS):\n        hash(c)\n\n\ndef test_asdict_complicated():\n    """\n    Benchmark instances with non-shortcut fields.\n    """\n    c = C()\n    ad = attrs.asdict\n\n    for _ in range(ROUNDS):\n        ad(c)\n\n\ndef test_astuple_complicated():\n    """\n    Benchmark instances with non-shortcut fields.\n    """\n    c = C()\n    at = attrs.astuple\n\n    for _ in range(ROUNDS):\n        at(c)\n\n\n@attrs.define\nclass AtomicFields:\n    a: int = 0\n    b: Ellipsis = ...\n    c: str = "foo"\n    d: tuple[str] = "bar"\n    e: complex = complex()\n\n\ndef test_asdict_atomic():\n    """\n    Benchmark atomic-only instances.\n    """\n    c = AtomicFields()\n    ad = attrs.asdict\n\n    for _ in range(ROUNDS):\n        ad(c)\n\n\ndef test_astuple_atomic():\n    """\n    Benchmark atomic-only instances.\n    """\n    c = AtomicFields()\n    at = attrs.astuple\n\n    for _ in range(ROUNDS):\n        at(c)\n',
        }
