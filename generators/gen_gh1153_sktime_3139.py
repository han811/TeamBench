"""
Parameterized generator for GH1153_sktime_3139.

Source PR:    https://github.com/sktime/sktime/pull/3139
Source Issue: N/A

Seed varies: renames 'breaking' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH1153_sktime_3139'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH1153_sktime_3139'
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
                files[fpath] = files[fpath].replace('breaking', 'breaking' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH1153_sktime_3139',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'sktime/sktime',
                "pr_number": 3139,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/sktime/sktime/pull/3139",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'sktime/tests/_config.py': '# -*- coding: utf-8 -*-\n\n__author__ = ["mloning"]\n__all__ = ["ESTIMATOR_TEST_PARAMS", "EXCLUDE_ESTIMATORS", "EXCLUDED_TESTS"]\n\nimport numpy as np\nfrom sklearn.preprocessing import FunctionTransformer, StandardScaler\n\nfrom sktime.annotation.clasp import ClaSPSegmentation\nfrom sktime.base import BaseEstimator\nfrom sktime.forecasting.structural import UnobservedComponents\nfrom sktime.registry import (\n    BASE_CLASS_LIST,\n    BASE_CLASS_LOOKUP,\n    ESTIMATOR_TAG_LIST,\n    TRANSFORMER_MIXIN_LIST,\n)\nfrom sktime.regression.compose import ComposableTimeSeriesForestRegressor\nfrom sktime.transformations.base import BaseTransformer\nfrom sktime.transformations.panel.compose import (\n    SeriesToPrimitivesRowTransformer,\n    SeriesToSeriesRowTransformer,\n)\nfrom sktime.transformations.panel.random_intervals import RandomIntervals\nfrom sktime.transformations.panel.shapelet_transform import RandomShapeletTransform\n\n# The following estimators currently do not pass all unit tests\n# https://github.com/alan-turing-institute/sktime/issues/1627\nEXCLUDE_ESTIMATORS = [\n    # SFA is non-compliant with any transformer interfaces, #2064\n    "SFA",\n    # requires y in fit, this is incompatible with the old testing framework\n    #    unless it inherits from the old mixins, which hard coded the y\n    #    should be removed once test_all_transformers has been refactored to scenarios\n    "TSFreshRelevantFeatureExtractor",\n    # PlateauFinder seems to be broken, see #2259\n    "PlateauFinder",\n]\n\n\nEXCLUDED_TESTS = {\n    # known issue when X is passed, wrong time indices are returned, #1364\n    "StackingForecaster": ["test_predict_time_index_with_X"],\n    # known side effects on multivariate arguments, #2072\n    "WindowSummarizer": ["test_methods_have_no_side_effects"],\n    # test fails in the Panel case for Differencer, see #2522\n    "Differencer": ["test_transform_inverse_transform_equivalent"],\n    # tagged in issue #2490\n    "SignatureClassifier": [\n        "test_classifier_on_unit_test_data",\n        "test_classifier_on_basic_motions",\n    ],\n    # test fail with deep problem with pickling inside tensorflow.\n    "CNNClassifier": [\n        "test_fit_idempotent",\n        "test_persistence_via_pickle",\n    ],\n    "CNNRegressor": [\n        "test_fit_idempotent",\n        "test_persistence_via_pickle",\n    ],\n    # pickling problem with local method see #2490\n    "ProximityStump": [\n        "test_persistence_via_pickle",\n        "test_fit_does_not_overwrite_hyper_params",\n    ],\n    "ProximityTree": [\n        "test_persistence_via_pickle",\n        "test_fit_does_not_overwrite_hyper_params",\n    ],\n    "ProximityForest": [\n        "test_persistence_via_pickle",\n        "test_fit_does_not_overwrite_hyper_params",\n    ],\n    # sth is not quite right with the RowTransformer-s changing state,\n    #   but these are anyway on their path to deprecation, see #2370\n    "SeriesToPrimitivesRowTransformer": ["test_methods_do_not_change_state"],\n    "SeriesToSeriesRowTransformer": ["test_methods_do_not_change_state"],\n    # ColumnTransformer still needs to be refactored, see #2537\n    "ColumnTransformer": ["test_methods_do_not_change_state"],\n    # Early classifiers intentionally retain information from pervious predict calls\n    #   for #1.\n    # #2 amd #3 are due to predict/predict_proba returning two items and that breaking\n    #   assert_array_equal\n    "TEASER": [\n        "test_methods_do_not_change_state",\n        "test_fit_idempotent",\n        "test_persistence_via_pickle",\n    ],\n    "VARMAX": "test_update_predict_single",  # see 2997, sporadic failure, unknown cause\n}\n\n# We here configure estimators for basic unit testing, including setting of\n# required hyper-parameters and setting of hyper-parameters for faster training.\nSERIES_TO_SERIES_TRANSFORMER = StandardScaler()\nSERIES_TO_PRIMITIVES_TRANSFORMER = FunctionTransformer(\n    np.mean, kw_args={"axis": 0}, check_inverse=False\n)\n\nESTIMATOR_TEST_PARAMS = {\n    SeriesToPrimitivesRowTransformer: {\n        "transformer": SERIES_TO_PRIMITIVES_TRANSFORMER,\n        "check_transformer": False,\n    },\n    SeriesToSeriesRowTransformer: {\n        "transformer": SERIES_TO_SERIES_TRANSFORMER,\n        "check_transformer": False,\n    },\n    RandomShapeletTransform: {\n        "max_shapelets": 5,\n        "n_shapelet_samples": 50,\n        "batch_size": 20,\n    },\n    RandomIntervals: {\n        "n_intervals": 3,\n    },\n    ComposableTimeSeriesForestRegressor: {"n_estimators": 3},\n    UnobservedComponents: {"level": "local level"},\n    ClaSPSegmentation: {"period_length": 5, "n_cps": 1},\n}\n\n# We use estimator tags in addition to class hierarchies to further distinguish\n# estimators into different categories. This is useful for defining and running\n# common tests for estimators with the same tags.\nVALID_ESTIMATOR_TAGS = tuple(ESTIMATOR_TAG_LIST)\n\n# These methods should not change the state of the estimator, that is, they should\n# not change fitted parameters or hyper-parameters. They are also the methods that\n# "apply" the fitted estimator to data and useful for checking results.\nNON_STATE_CHANGING_METHODS = (\n    "predict",\n    "predict_var",\n    "predict_proba",\n    "decision_function",\n    "transform",\n    # todo: add this back\n    # escaping this, since for some estimators\n    #   the input format of inverse_transform assumes special col names\n    # "inverse_transform",\n)\n\n# The following gives a list of valid estimator base classes.\nVALID_TRANSFORMER_TYPES = tuple(TRANSFORMER_MIXIN_LIST) + (BaseTransformer,)\n\nVALID_ESTIMATOR_BASE_TYPES = tuple(BASE_CLASS_LIST)\n\nVALID_ESTIMATOR_TYPES = (\n    BaseEstimator,\n    *VALID_ESTIMATOR_BASE_TYPES,\n    *VALID_TRANSFORMER_TYPES,\n)\n\nVALID_ESTIMATOR_BASE_TYPE_LOOKUP = BASE_CLASS_LOOKUP\n',
        }
