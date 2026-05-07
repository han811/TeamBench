"""
Parameterized generator for GH1083_sktime_3207.

Source PR:    https://github.com/sktime/sktime/pull/3207
Source Issue: N/A

Seed varies: renames 'commented' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH1083_sktime_3207'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH1083_sktime_3207'
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
                files[fpath] = files[fpath].replace('commented', 'commented' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH1083_sktime_3207',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'sktime/sktime',
                "pr_number": 3207,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/sktime/sktime/pull/3207",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'sktime/classification/dictionary_based/tests/test_tde.py': '# -*- coding: utf-8 -*-\n"""TDE test code."""\nimport numpy as np\n\nfrom sktime.classification.dictionary_based._tde import TemporalDictionaryEnsemble\nfrom sktime.datasets import load_unit_test\n\n\ndef test_tde_train_estimate():\n    """Test of TDE train estimate on unit test data."""\n    # load unit test data\n    X_train, y_train = load_unit_test(split="train")\n\n    # train TDE\n    tde = TemporalDictionaryEnsemble(\n        n_parameter_samples=5,\n        max_ensemble_size=2,\n        randomly_selected_params=3,\n        random_state=0,\n    )\n    tde.fit(X_train, y_train)\n\n    # test oob estimate\n    train_proba = tde._get_train_probs(X_train, y_train, train_estimate_method="oob")\n    assert isinstance(train_proba, np.ndarray)\n    assert train_proba.shape == (len(X_train), 2)\n    np.testing.assert_almost_equal(train_proba.sum(axis=1), 1, decimal=4)\n\n\ndef test_contracted_tde():\n    """Test of contracted TDE on unit test data."""\n    # load unit test data\n    X_train, y_train = load_unit_test(split="train")\n\n    # train contracted TDE\n    tde = TemporalDictionaryEnsemble(\n        time_limit_in_minutes=0.25,\n        contract_max_n_parameter_samples=5,\n        max_ensemble_size=2,\n        randomly_selected_params=3,\n        random_state=0,\n    )\n    tde.fit(X_train, y_train)\n\n    assert len(tde.estimators_) > 1\n',
            'sktime/classification/interval_based/tests/test_drcif.py': '# -*- coding: utf-8 -*-\n"""DrCIF test code."""\nfrom sktime.classification.interval_based import DrCIF\nfrom sktime.datasets import load_unit_test\n\n\ndef test_contracted_drcif():\n    """Test of contracted DrCIF on unit test data."""\n    # load unit test data\n    X_train, y_train = load_unit_test(split="train")\n\n    # train contracted DrCIF\n    drcif = DrCIF(\n        time_limit_in_minutes=0.25,\n        contract_max_n_estimators=2,\n        n_intervals=2,\n        att_subsample_size=2,\n        random_state=0,\n    )\n    drcif.fit(X_train, y_train)\n\n    assert len(drcif.estimators_) > 1\n',
            'sktime/classification/shapelet_based/tests/test_stc.py': '# -*- coding: utf-8 -*-\n"""ShapeletTransformClassifier test code."""\nfrom sktime.classification.shapelet_based import ShapeletTransformClassifier\nfrom sktime.classification.sklearn import RotationForest\nfrom sktime.datasets import load_unit_test\n\n\ndef test_contracted_stc():\n    """Test of contracted ShapeletTransformClassifier on unit test data."""\n    # load unit test data\n    X_train, y_train = load_unit_test(split="train")\n\n    # train contracted STC\n    stc = ShapeletTransformClassifier(\n        estimator=RotationForest(contract_max_n_estimators=2, random_state=0),\n        max_shapelets=3,\n        time_limit_in_minutes=0.25,\n        contract_max_n_shapelet_samples=10,\n        batch_size=5,\n        random_state=0,\n    )\n    stc.fit(X_train, y_train)\n\n    assert len(stc._estimator.estimators_) > 1\n',
        }
