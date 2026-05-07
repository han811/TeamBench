"""
Parameterized generator for GH1130_sktime_6713.

Source PR:    https://github.com/sktime/sktime/pull/6713
Source Issue: N/A

Seed varies: renames 'accept' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH1130_sktime_6713'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH1130_sktime_6713'
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
                files[fpath] = files[fpath].replace('accept', 'accept' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH1130_sktime_6713',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'sktime/sktime',
                "pr_number": 6713,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/sktime/sktime/pull/6713",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'sktime/forecasting/tests/test_interval_wrappers.py': '# copyright: sktime developers, BSD-3-Clause License (see LICENSE file)\n"""Tests the conformal interval wrapper."""\n\n__author__ = ["fkiraly", "bethrice44"]\n\nimport numpy as np\nimport pandas as pd\nimport pytest\n\nfrom sktime.datasets import load_airline\nfrom sktime.datatypes import convert_to, scitype_to_mtype\nfrom sktime.forecasting.conformal import ConformalIntervals\nfrom sktime.forecasting.model_evaluation import evaluate\nfrom sktime.forecasting.naive import NaiveForecaster, NaiveVariance\nfrom sktime.performance_metrics.forecasting.probabilistic import PinballLoss\nfrom sktime.split import ExpandingWindowSplitter, SlidingWindowSplitter\nfrom sktime.tests.test_switch import run_test_for_class\n\nINTERVAL_WRAPPERS = [ConformalIntervals, NaiveVariance]\nCV_SPLITTERS = [SlidingWindowSplitter, ExpandingWindowSplitter]\nEVALUATE_STRATEGY = ["update", "refit"]\nSAMPLE_FRACS = [None, 0.5]\nMTYPES_SERIES = scitype_to_mtype("Series", softdeps="present")\n\n\n@pytest.mark.skipif(\n    not run_test_for_class(INTERVAL_WRAPPERS),\n    reason="run test only if softdeps are present and incrementally (if requested)",\n)\n@pytest.mark.parametrize("mtype", MTYPES_SERIES)\n@pytest.mark.parametrize("override_y_mtype", [True, False])\n@pytest.mark.parametrize("wrapper", INTERVAL_WRAPPERS)\ndef test_wrapper_series_mtype(wrapper, override_y_mtype, mtype):\n    """Test that interval wrappers behave nicely with different internal y_mtypes.\n\n    The wrappers require y to be pd.Series, and the internal estimator can have\n    a different internal mtype.\n\n    We test all interval wrappers in sktime (wrapper).\n\n    We test once with an internal forecaster that needs pd.DataFrame conversion,\n    and one that accepts pd.Series.\n    We do this with a trick: the vanilla NaiveForecaster can accept both; we mimic a\n    "pd.DataFrame only" forecaster by restricting its y_inner_mtype tag to pd.Series.\n    """\n    y = load_airline()\n    y = convert_to(y, to_type=mtype)\n\n    f = NaiveForecaster()\n\n    if override_y_mtype:\n        f.set_tags(**{"y_inner_mtype": "pd.DataFrame"})\n\n    interval_forecaster = wrapper(f)\n    interval_forecaster.fit(y, fh=[1, 2, 3])\n    pred_int = interval_forecaster.predict_interval()\n\n    assert isinstance(pred_int, pd.DataFrame)\n    assert len(pred_int) == 3\n\n    pred_var = interval_forecaster.predict_var()\n\n    assert isinstance(pred_var, pd.DataFrame)\n    assert len(pred_var) == 3\n\n\n@pytest.mark.skipif(\n    not run_test_for_class(INTERVAL_WRAPPERS + [evaluate]),\n    reason="run test only if softdeps are present and incrementally (if requested)",\n)\n@pytest.mark.parametrize("wrapper", INTERVAL_WRAPPERS)\n@pytest.mark.parametrize("splitter", CV_SPLITTERS)\n@pytest.mark.parametrize("strategy", EVALUATE_STRATEGY)\n@pytest.mark.parametrize("sample_frac", SAMPLE_FRACS)\ndef test_evaluate_with_window_splitters(wrapper, splitter, strategy, sample_frac):\n    """Test interval wrappers with different strategies and cross validators.\n\n    The wrapper does some internal sliding window cross-validation to calculate the\n    `residuals_matrix`, which means the initial cross-validation can cause issues.\n\n    This checks refit and update strategies as well as expanding and sliding window\n    splitters.\n    """\n    y = load_airline()[:60]\n\n    if splitter == SlidingWindowSplitter:\n        cv = splitter(\n            fh=np.arange(1, 7),\n            window_length=24,\n            step_length=6,\n        )\n    elif splitter == ExpandingWindowSplitter:\n        cv = splitter(\n            fh=np.arange(1, 7),\n            initial_window=24,\n            step_length=6,\n        )\n\n    f = NaiveForecaster()\n\n    if wrapper == ConformalIntervals:\n        interval_forecaster = wrapper(f, initial_window=12, sample_frac=sample_frac)\n    else:\n        interval_forecaster = wrapper(f, initial_window=12)\n\n    results = evaluate(\n        forecaster=interval_forecaster,\n        cv=cv,\n        y=y,\n        X=None,\n        strategy=strategy,\n        scoring=PinballLoss(alpha=[0.1, 0.5, 0.9]),\n        return_data=True,\n        error_score="raise",\n        backend=None,\n    )\n\n    assert len(results) == 6\n    assert not results.test_PinballLoss.isna().any()\n',
        }
