"""
Parameterized generator for GH1221_plotly.py_5361.

Source PR:    https://github.com/plotly/plotly.py/pull/5361
Source Issue: N/A

Seed varies: renames 'assert_allclose' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH1221_plotly.py_5361'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH1221_plotly.py_5361'
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
            task_id='GH1221_plotly.py_5361',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'plotly/plotly.py',
                "pr_number": 5361,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/plotly/plotly.py/pull/5361",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'plotly/matplotlylib/mplexporter/tests/test_utils.py': 'from numpy.testing import assert_allclose, assert_equal\nfrom .. import utils\nimport matplotlib.pyplot as plt\n\n\ndef test_path_data():\n    circle = plt.Circle((0, 0), 1)\n    vertices, codes = utils.SVG_path(circle.get_path())\n\n    assert_allclose(vertices.shape, (25, 2))\n    assert_equal(codes, ["M", "C", "C", "C", "C", "C", "C", "C", "C", "Z"])\n\n\ndef test_linestyle():\n    linestyles = {\n        "solid": "none",\n        "-": "none",\n        "dashed": "5.550000000000001,2.4000000000000004",\n        "--": "5.550000000000001,2.4000000000000004",\n        "dotted": "1.5,2.4749999999999996",\n        ":": "1.5,2.4749999999999996",\n        "dashdot": "9.600000000000001,2.4000000000000004,1.5,2.4000000000000004",\n        "-.": "9.600000000000001,2.4000000000000004,1.5,2.4000000000000004",\n        "": None,\n        "None": None,\n    }\n\n    for ls, result in linestyles.items():\n        (line,) = plt.plot([1, 2, 3], linestyle=ls)\n        assert_equal(utils.get_dasharray(line), result)\n\n\ndef test_axis_w_fixed_formatter():\n    positions, labels = [0, 1, 10], ["A", "B", "C"]\n\n    plt.xticks(positions, labels)\n    props = utils.get_axis_properties(plt.gca().xaxis)\n\n    assert_equal(props["tickvalues"], positions)\n    assert_equal(props["tickformat"], labels)\n',
            'plotly/matplotlylib/tests/test_renderer.py': 'import plotly.tools as tls\n\nfrom . import plt\n\n\ndef test_native_legend_enabled_when_matplotlib_legend_present():\n    """Test that when matplotlib legend is present, Plotly uses native legend."""\n    fig, ax = plt.subplots()\n    ax.plot([0, 1], [0, 1], label="Line 1")\n    ax.plot([0, 1], [1, 0], label="Line 2")\n    ax.legend()\n\n    plotly_fig = tls.mpl_to_plotly(fig)\n\n    # Should enable native legend\n    assert plotly_fig.layout.showlegend == True\n    # Should have 2 traces with names\n    assert len(plotly_fig.data) == 2\n    assert plotly_fig.data[0].name == "Line 1"\n    assert plotly_fig.data[1].name == "Line 2"\n\n\ndef test_no_fake_legend_shapes_with_native_legend():\n    """Test that fake legend shapes are not created when using native legend."""\n    fig, ax = plt.subplots()\n    ax.plot([0, 1], [0, 1], "o-", label="Data with markers")\n    ax.legend()\n\n    plotly_fig = tls.mpl_to_plotly(fig)\n\n    # Should use native legend\n    assert plotly_fig.layout.showlegend == True\n    # Should not create fake legend elements\n    assert len(plotly_fig.layout.shapes) == 0\n    assert len(plotly_fig.layout.annotations) == 0\n\n\ndef test_legend_disabled_when_no_matplotlib_legend():\n    """Test that legend is not enabled when no matplotlib legend is present."""\n    fig, ax = plt.subplots()\n    ax.plot([0, 1], [0, 1], label="Line 1")  # Has label but no legend() call\n\n    plotly_fig = tls.mpl_to_plotly(fig)\n\n    # Should not have showlegend explicitly set to True\n    # (Plotly\'s default behavior when no legend elements exist)\n    assert (\n        not hasattr(plotly_fig.layout, "showlegend")\n        or plotly_fig.layout.showlegend != True\n    )\n\n\ndef test_legend_disabled_when_matplotlib_legend_not_visible():\n    """Test that legend is not enabled when no matplotlib legend is not visible."""\n    fig, ax = plt.subplots()\n    ax.plot([0, 1], [0, 1], label="Line 1")\n    legend = ax.legend()\n    legend.set_visible(False)  # Hide the legend\n\n    plotly_fig = tls.mpl_to_plotly(fig)\n\n    # Should not enable legend when matplotlib legend is hidden\n    assert (\n        not hasattr(plotly_fig.layout, "showlegend")\n        or plotly_fig.layout.showlegend != True\n    )\n\n\ndef test_multiple_traces_native_legend():\n    """Test native legend works with multiple traces of different types."""\n    fig, ax = plt.subplots()\n    ax.plot([0, 1, 2], [0, 1, 0], "-", label="Line")\n    ax.plot([0, 1, 2], [1, 0, 1], "o", label="Markers")\n    ax.plot([0, 1, 2], [0.5, 0.5, 0.5], "s-", label="Line+Markers")\n    ax.legend()\n\n    plotly_fig = tls.mpl_to_plotly(fig)\n\n    assert plotly_fig.layout.showlegend == True\n    assert len(plotly_fig.data) == 3\n    assert plotly_fig.data[0].name == "Line"\n    assert plotly_fig.data[1].name == "Markers"\n    assert plotly_fig.data[2].name == "Line+Markers"\n    # Verify modes are correct\n    assert plotly_fig.data[0].mode == "lines"\n    assert plotly_fig.data[1].mode == "markers"\n    assert plotly_fig.data[2].mode == "lines+markers"\n',
        }
