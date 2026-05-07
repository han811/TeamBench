"""
Parameterized generator for GH337_napari_7018.

Source PR:    https://github.com/napari/napari/pull/7018
Source Issue: N/A

Seed varies: renames 'account' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH337_napari_7018'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH337_napari_7018'
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
                files[fpath] = files[fpath].replace('account', 'account' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH337_napari_7018',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'napari/napari',
                "pr_number": 7018,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/napari/napari/pull/7018",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'napari/_vispy/_tests/test_vispy_scale_bar_visual.py': 'from napari._vispy.overlays.scale_bar import VispyScaleBarOverlay\nfrom napari.components.overlays import ScaleBarOverlay\n\n\ndef test_scale_bar_instantiation(make_napari_viewer):\n    viewer = make_napari_viewer()\n    model = ScaleBarOverlay()\n    vispy_scale_bar = VispyScaleBarOverlay(overlay=model, viewer=viewer)\n    assert vispy_scale_bar.overlay.length is None\n    model.length = 50\n    assert vispy_scale_bar.overlay.length == 50\n',
            'napari/_vispy/overlays/scale_bar.py': 'import bisect\nfrom decimal import Decimal\nfrom math import floor, log\n\nimport numpy as np\nimport pint\n\nfrom napari._vispy.overlays.base import ViewerOverlayMixin, VispyCanvasOverlay\nfrom napari._vispy.visuals.scale_bar import ScaleBar\nfrom napari.utils._units import PREFERRED_VALUES, get_unit_registry\nfrom napari.utils.colormaps.standardize_color import transform_color\nfrom napari.utils.theme import get_theme\n\n\nclass VispyScaleBarOverlay(ViewerOverlayMixin, VispyCanvasOverlay):\n    """Scale bar in world coordinates."""\n\n    def __init__(self, *, viewer, overlay, parent=None) -> None:\n        self._target_length = 150.0\n        self._scale = 1\n        self._unit: pint.Unit\n\n        super().__init__(\n            node=ScaleBar(), viewer=viewer, overlay=overlay, parent=parent\n        )\n        self.x_size = 150  # will be updated on zoom anyways\n        # need to change from defaults because the anchor is in the center\n        self.y_offset = 20\n        self.y_size = 5\n\n        self.overlay.events.box.connect(self._on_box_change)\n        self.overlay.events.box_color.connect(self._on_data_change)\n        self.overlay.events.color.connect(self._on_data_change)\n        self.overlay.events.colored.connect(self._on_data_change)\n        self.overlay.events.font_size.connect(self._on_text_change)\n        self.overlay.events.ticks.connect(self._on_data_change)\n        self.overlay.events.unit.connect(self._on_unit_change)\n        self.overlay.events.length.connect(self._on_length_change)\n\n        self.viewer.events.theme.connect(self._on_data_change)\n        self.viewer.camera.events.zoom.connect(self._on_zoom_change)\n\n        self.reset()\n\n    def _on_unit_change(self):\n        self._unit = get_unit_registry()(self.overlay.unit)\n        self._on_zoom_change(force=True)\n\n    def _on_length_change(self):\n        self._on_zoom_change(force=True)\n\n    def _calculate_best_length(\n        self, desired_length: float\n    ) -> tuple[float, pint.Quantity]:\n        """Calculate new quantity based on the pixel length of the bar.\n\n        Parameters\n        ----------\n        desired_length : float\n            Desired length of the scale bar in world size.\n\n        Returns\n        -------\n        new_length : float\n            New length of the scale bar in world size based\n            on the preferred scale bar value.\n        new_quantity : pint.Quantity\n            New quantity with abbreviated base unit.\n        """\n        current_quantity = self._unit * desired_length\n        # convert the value to compact representation\n        new_quantity = current_quantity.to_compact()\n        # calculate the scaling factor taking into account any conversion\n        # that might have occurred (e.g. um -> cm)\n        factor = current_quantity / new_quantity\n\n        # select value closest to one of our preferred values and also\n        # validate if quantity is dimensionless and lower than 1 to prevent\n        # the scale bar to extend beyond the canvas when zooming.\n        # If the value falls in those conditions, we use the corresponding\n        # preferred value but scaled to take into account the actual value\n        # magnitude. See https://github.com/napari/napari/issues/5914\n        magnitude_1000 = floor(log(new_quantity.magnitude, 1000))\n        scaled_magnitude = new_quantity.magnitude * 1000 ** (-magnitude_1000)\n        index = bisect.bisect_left(PREFERRED_VALUES, scaled_magnitude)\n        if index > 0:\n            # When we get the lowest index of the list, removing -1 will\n            # return the last index.\n            index -= 1\n        new_value: float = PREFERRED_VALUES[index]\n        if new_quantity.dimensionless and new_quantity.magnitude < 1:\n            # using Decimal is necessary to avoid `4.999999e-6`\n            # at really small scale.\n            new_value = float(\n                Decimal(new_value) * Decimal(1000) ** magnitude_1000\n            )\n\n        # get the new pixel length utilizing the user-specified units\n        new_length = (\n            (new_value * factor) / (1 * self._unit).magnitude\n        ).magnitude\n        new_quantity = new_value * new_quantity.units\n        return new_length, new_quantity\n\n    def _on_zoom_change(self, *, force: bool = False):\n        """Update axes length based on zoom scale."""\n\n        # If scale has not changed, do not redraw\n        scale = 1 / self.viewer.camera.zoom\n        if abs(np.log10(self._scale) - np.log10(scale)) < 1e-4 and not force:\n            return\n        self._scale = scale\n\n        scale_canvas2world = self._scale\n        target_canvas_pixels = self._target_length\n        # convert desired length to world size\n        target_world_pixels = scale_canvas2world * target_canvas_pixels\n\n        # If length is set, use that value to calculate the scale bar length\n        if self.overlay.length is not None:\n            target_canvas_pixels = self.overlay.length / scale_canvas2world\n            new_dim = self.overlay.length * self._unit.units\n        else:\n            # calculate the desired length as well as update the value and units\n            target_world_pixels_rounded, new_dim = self._calculate_best_length(\n                target_world_pixels\n            )\n            target_canvas_pixels = (\n                target_world_pixels_rounded / scale_canvas2world\n            )\n\n        scale = target_canvas_pixels\n\n        # Update scalebar and text\n        self.node.transform.scale = [scale, 1, 1, 1]\n        self.node.text.text = f\'{new_dim:g~#P}\'\n        self.x_size = scale  # needed to offset properly\n        self._on_position_change()\n\n    def _on_data_change(self):\n        """Change color and data of scale bar and box."""\n        color = self.overlay.color\n        box_color = self.overlay.box_color\n\n        if not self.overlay.colored:\n            if self.overlay.box:\n                # The box is visible - set the scale bar color to the negative of the\n                # box color.\n                color = 1 - box_color\n                color[-1] = 1\n            else:\n                # set scale color negative of theme background.\n                # the reason for using the `as_hex` here is to avoid\n                # `UserWarning` which is emitted when RGB values are above 1\n                if (\n                    self.node.parent is not None\n                    and self.node.parent.canvas.bgcolor\n                ):\n                    background_color = self.node.parent.canvas.bgcolor.rgba\n                else:\n                    background_color = get_theme(\n                        self.viewer.theme\n                    ).canvas.as_hex()\n                    background_color = transform_color(background_color)[0]\n                color = np.subtract(1, background_color)\n                color[-1] = background_color[-1]\n\n        self.node.set_data(color, self.overlay.ticks)\n        self.node.box.color = box_color\n\n    def _on_box_change(self):\n        self.node.box.visible = self.overlay.box\n\n    def _on_text_change(self):\n        """Update text information"""\n        self.node.text.font_size = self.overlay.font_size\n\n    def reset(self):\n        super().reset()\n        self._on_unit_change()\n        self._on_data_change()\n        self._on_box_change()\n        self._on_text_change()\n        self._on_length_change()\n',
        }
