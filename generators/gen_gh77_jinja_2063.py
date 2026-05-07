"""
Parameterized generator for GH77_jinja_2063.

Source PR:    https://github.com/pallets/jinja/pull/2063
Source Issue: https://github.com/pallets/jinja/issues/2010

Seed varies: renames 'behaviors' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH77_jinja_2063'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH77_jinja_2063'
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
                files[fpath] = files[fpath].replace('behaviors', 'behaviors' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH77_jinja_2063',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'pallets/jinja',
                "pr_number": 2063,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/pallets/jinja/pull/2063",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'docs/nativetypes.rst': ".. module:: jinja2.nativetypes\n\n.. _nativetypes:\n\nNative Python Types\n===================\n\nThe default :class:`~jinja2.Environment` renders templates to strings. With\n:class:`NativeEnvironment`, rendering a template produces a native Python type.\nThis is useful if you are using Jinja outside the context of creating text\nfiles. For example, your code may have an intermediate step where users may use\ntemplates to define values that will then be passed to a traditional string\nenvironment.\n\nExamples\n--------\n\nAdding two values results in an integer, not a string with a number:\n\n>>> env = NativeEnvironment()\n>>> t = env.from_string('{{ x + y }}')\n>>> result = t.render(x=4, y=2)\n>>> print(result)\n6\n>>> print(type(result))\nint\n\nRendering list syntax produces a list:\n\n>>> t = env.from_string('[{% for item in data %}{{ item + 1 }},{% endfor %}]')\n>>> result = t.render(data=range(5))\n>>> print(result)\n[1, 2, 3, 4, 5]\n>>> print(type(result))\nlist\n\nRendering something that doesn't look like a Python literal produces a string:\n\n>>> t = env.from_string('{{ x }} * {{ y }}')\n>>> result = t.render(x=4, y=2)\n>>> print(result)\n4 * 2\n>>> print(type(result))\nstr\n\nRendering a Python object produces that object as long as it is the only node:\n\n>>> class Foo:\n...     def __init__(self, value):\n...         self.value = value\n...\n>>> result = env.from_string('{{ x }}').render(x=Foo(15))\n>>> print(type(result).__name__)\nFoo\n>>> print(result.value)\n15\n\nAPI\n---\n\n.. autoclass:: NativeEnvironment([options])\n\n.. autoclass:: NativeTemplate([options])\n    :members: render\n",
        }
