"""
Parameterized generator for GH898_plotly.py_5322.

Source PR:    https://github.com/plotly/plotly.py/pull/5322
Source Issue: https://github.com/plotly/plotly.py/issues/5253

Seed varies: renames 'assert_allclose' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH898_plotly.py_5322'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH898_plotly.py_5322'
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
                files[fpath] = files[fpath].replace('assert_allclose', 'assert_allclose' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH898_plotly.py_5322',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'plotly/plotly.py',
                "pr_number": 5322,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/plotly/plotly.py/pull/5322",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'plotly/matplotlylib/mplexporter/tests/test_utils.py': 'from numpy.testing import assert_allclose, assert_equal\nfrom . import plt\nfrom .. import utils\n\n\ndef test_path_data():\n    circle = plt.Circle((0, 0), 1)\n    vertices, codes = utils.SVG_path(circle.get_path())\n\n    assert_allclose(vertices.shape, (25, 2))\n    assert_equal(codes, ["M", "C", "C", "C", "C", "C", "C", "C", "C", "Z"])\n\n\ndef test_linestyle():\n    linestyles = {\n        "solid": "none",\n        "-": "none",\n        "dashed": "5.550000000000001,2.4000000000000004",\n        "--": "5.550000000000001,2.4000000000000004",\n        "dotted": "1.5,2.4749999999999996",\n        ":": "1.5,2.4749999999999996",\n        "dashdot": "9.600000000000001,2.4000000000000004,1.5,2.4000000000000004",\n        "-.": "9.600000000000001,2.4000000000000004,1.5,2.4000000000000004",\n        "": None,\n        "None": None,\n    }\n\n    for ls, result in linestyles.items():\n        (line,) = plt.plot([1, 2, 3], linestyle=ls)\n        assert_equal(utils.get_dasharray(line), result)\n\n\ndef test_axis_w_fixed_formatter():\n    positions, labels = [0, 1, 10], ["A", "B", "C"]\n\n    plt.xticks(positions, labels)\n    props = utils.get_axis_properties(plt.gca().xaxis)\n\n    assert_equal(props["tickvalues"], positions)\n    assert_equal(props["tickformat"], labels)\n',
        }
