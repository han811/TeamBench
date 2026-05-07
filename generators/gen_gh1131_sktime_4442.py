"""
Parameterized generator for GH1131_sktime_4442.

Source PR:    https://github.com/sktime/sktime/pull/4442
Source Issue: N/A

Seed varies: renames 'addition' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH1131_sktime_4442'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH1131_sktime_4442'
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
                files[fpath] = files[fpath].replace('addition', 'addition' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH1131_sktime_4442',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'sktime/sktime',
                "pr_number": 4442,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/sktime/sktime/pull/4442",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'sktime/tests/_config.py': '# -*- coding: utf-8 -*-\n\n__author__ = ["mloning"]\n__all__ = ["EXCLUDE_ESTIMATORS", "EXCLUDED_TESTS"]\n\nfrom sktime.base import BaseEstimator, BaseObject\nfrom sktime.registry import (\n    BASE_CLASS_LIST,\n    BASE_CLASS_LOOKUP,\n    ESTIMATOR_TAG_LIST,\n    TRANSFORMER_MIXIN_LIST,\n)\nfrom sktime.transformations.base import BaseTransformer\n\nEXCLUDE_ESTIMATORS = [\n    # SFA is non-compliant with any transformer interfaces, #2064\n    "SFA",\n    # PlateauFinder seems to be broken, see #2259\n    "PlateauFinder",\n    # below are removed due to mac failures we don\'t fully understand, see #3103\n    "HIVECOTEV1",\n    "HIVECOTEV2",\n    "RandomIntervalSpectralEnsemble",\n    "RandomInvervals",\n    "RandomIntervalSegmenter",\n    "RandomIntervalFeatureExtractor",\n    "RandomIntervalClassifier",\n    "MiniRocket",\n    "MatrixProfileTransformer",\n    # tapnet based estimators fail stochastically for unknown reasons, see #3525\n    "TapNetRegressor",\n    "TapNetClassifier",\n    "ResNetClassifier",  # known ResNetClassifier sporafic failures, see #3954\n    "LSTMFCNClassifier",  # unknown cause, see bug report #4033\n    "TimeSeriesLloyds",  # an abstract class, but does not follow naming convention\n]\n\n\nEXCLUDED_TESTS = {\n    # issue when predicting residuals, see #3479\n    # known issue with prediction intervals that needs fixing, tracked in #4181\n    "SquaringResiduals": ["test_predict_residuals", "test_predict_interval"],\n    # known issue when X is passed, wrong time indices are returned, #1364\n    "StackingForecaster": ["test_predict_time_index_with_X"],\n    # known side effects on multivariate arguments, #2072\n    "WindowSummarizer": ["test_methods_have_no_side_effects"],\n    # test fails in the Panel case for Differencer, see #2522\n    "Differencer": ["test_transform_inverse_transform_equivalent"],\n    # tagged in issue #2490\n    "SignatureClassifier": [\n        "test_classifier_on_unit_test_data",\n        "test_classifier_on_basic_motions",\n    ],\n    # pickling problem with local method see #2490\n    "ProximityStump": [\n        "test_persistence_via_pickle",\n        "test_fit_does_not_overwrite_hyper_params",\n        "test_save_estimators_to_file",\n    ],\n    "ProximityTree": [\n        "test_persistence_via_pickle",\n        "test_fit_does_not_overwrite_hyper_params",\n        "test_save_estimators_to_file",\n    ],\n    "ProximityForest": [\n        "test_persistence_via_pickle",\n        "test_fit_does_not_overwrite_hyper_params",\n        "test_save_estimators_to_file",\n    ],\n    # TapNet fails due to Lambda layer, see #3539 and #3616\n    "TapNetClassifier": [\n        "test_fit_idempotent",\n        "test_persistence_via_pickle",\n        "test_save_estimators_to_file",\n    ],\n    "TapNetRegressor": [\n        "test_fit_idempotent",\n        "test_persistence_via_pickle",\n        "test_save_estimators_to_file",\n    ],\n    # `test_fit_idempotent` fails with `AssertionError`, see #3616\n    "ResNetClassifier": [\n        "test_fit_idempotent",\n    ],\n    "CNNClassifier": [\n        "test_fit_idempotent",\n    ],\n    "CNNRegressor": [\n        "test_fit_idempotent",\n    ],\n    "FCNClassifier": [\n        "test_fit_idempotent",\n    ],\n    "LSTMFCNClassifier": [\n        "test_fit_idempotent",\n    ],\n    "MLPClassifier": [\n        "test_fit_idempotent",\n    ],\n    # sth is not quite right with the RowTransformer-s changing state,\n    #   but these are anyway on their path to deprecation, see #2370\n    "SeriesToPrimitivesRowTransformer": ["test_methods_do_not_change_state"],\n    "SeriesToSeriesRowTransformer": ["test_methods_do_not_change_state"],\n    # ColumnTransformer still needs to be refactored, see #2537\n    "ColumnTransformer": ["test_methods_do_not_change_state"],\n    # Early classifiers intentionally retain information from previous predict calls\n    #   for #1.\n    # #2 amd #3 are due to predict/predict_proba returning two items and that breaking\n    #   assert_array_equal\n    "TEASER": [\n        "test_non_state_changing_method_contract",\n        "test_fit_idempotent",\n        "test_persistence_via_pickle",\n        "test_save_estimators_to_file",\n    ],\n    "CNNNetwork": "test_inheritance",  # not a registered base class, WiP, see #3028\n    "VARMAX": [\n        "test_update_predict_single",  # see 2997, sporadic failure, unknown cause\n        "test__y_when_refitting",  # see 3176\n    ],\n    # GGS inherits from BaseEstimator which breaks this test\n    "GreedyGaussianSegmentation": ["test_inheritance", "test_create_test_instance"],\n    "InformationGainSegmentation": [\n        "test_inheritance",\n        "test_create_test_instance",\n    ],\n    # SAX returns strange output format\n    # this needs to be fixed, was not tested previously due to legacy exception\n    "SAX": "test_fit_transform_output",\n    # known bug in BaggingForecaster, returns wrong index, #4363\n    "BaggingForecaster": [\n        "test_predict_interval",\n        "test_predict_quantiles",\n        "test_predict_proba",\n    ],\n    # known bug in DynamicFactor, returns wrong index, #4362\n    "DynamicFactor": [\n        "test_predict_interval",\n        "test_predict_quantiles",\n        "test_predict_proba",\n    ],\n    # stochastic failure of quantile prediction monotonicity, refer to #4420, #4431\n    "VAR": ["test_predict_quantiles"],\n    "Prophet": ["test_predict_quantiles"],\n}\n\n# We use estimator tags in addition to class hierarchies to further distinguish\n# estimators into different categories. This is useful for defining and running\n# common tests for estimators with the same tags.\nVALID_ESTIMATOR_TAGS = tuple(ESTIMATOR_TAG_LIST)\n\n# NON_STATE_CHANGING_METHODS =\n# methods that should not change the state of the estimator, that is, they should\n# not change fitted parameters or hyper-parameters. They are also the methods that\n# "apply" the fitted estimator to data and useful for checking results.\n# NON_STATE_CHANGING_METHODS_ARRAYLIK =\n# non-state-changing methods that return an array-like output\n\nNON_STATE_CHANGING_METHODS_ARRAYLIKE = (\n    "predict",\n    "predict_var",\n    "predict_proba",\n    "decision_function",\n    "transform",\n    # todo: add this back\n    # escaping this, since for some estimators\n    #   the input format of inverse_transform assumes special col names\n    # "inverse_transform",\n)\n\nNON_STATE_CHANGING_METHODS = NON_STATE_CHANGING_METHODS_ARRAYLIKE + (\n    "get_fitted_params",\n)\n\n# The following gives a list of valid estimator base classes.\nVALID_TRANSFORMER_TYPES = tuple(TRANSFORMER_MIXIN_LIST) + (BaseTransformer,)\n\nBASE_BASE_TYPES = (BaseEstimator, BaseObject)\nVALID_ESTIMATOR_BASE_TYPES = tuple(set(BASE_CLASS_LIST).difference(BASE_BASE_TYPES))\n\nVALID_ESTIMATOR_TYPES = (\n    BaseEstimator,\n    *VALID_ESTIMATOR_BASE_TYPES,\n    *VALID_TRANSFORMER_TYPES,\n)\n\nVALID_ESTIMATOR_BASE_TYPE_LOOKUP = BASE_CLASS_LOOKUP\n',
        }
