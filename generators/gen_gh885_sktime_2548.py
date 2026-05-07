"""
Parameterized generator for GH885_sktime_2548.

Source PR:    https://github.com/sktime/sktime/pull/2548
Source Issue: https://github.com/sktime/sktime/issues/1234

Seed varies: renames 'array_equal' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH885_sktime_2548'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH885_sktime_2548'
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
                files[fpath] = files[fpath].replace('array_equal', 'array_equal' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH885_sktime_2548',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'sktime/sktime',
                "pr_number": 2548,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/sktime/sktime/pull/2548",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'sktime/clustering/k_medoids.py': '# -*- coding: utf-8 -*-\n"""Time series kmedoids."""\n__author__ = ["chrisholder", "TonyBagnall"]\n\nfrom typing import Callable, Union\n\nimport numpy as np\nfrom numpy.random import RandomState\n\nfrom sktime.clustering.metrics.medoids import medoids\nfrom sktime.clustering.partitioning import TimeSeriesLloyds\nfrom sktime.distances import pairwise_distance\n\n\nclass TimeSeriesKMedoids(TimeSeriesLloyds):\n    """Time series K-medoids implementation.\n\n    Parameters\n    ----------\n    n_clusters: int, defaults = 8\n        The number of clusters to form as well as the number of\n        centroids to generate.\n    init_algorithm: str, defaults = \'forgy\'\n        Method for initializing cluster centers. Any of the following are valid:\n        [\'kmeans++\', \'random\', \'forgy\']\n    metric: str or Callable, defaults = \'dtw\'\n        Distance metric to compute similarity between time series. Any of the following\n        are valid: [\'dtw\', \'euclidean\', \'erp\', \'edr\', \'lcss\', \'squared\', \'ddtw\', \'wdtw\',\n        \'wddtw\']\n    n_init: int, defaults = 10\n        Number of times the k-means algorithm will be run with different\n        centroid seeds. The final result will be the best output of n_init\n        consecutive runs in terms of inertia.\n    max_iter: int, defaults = 30\n        Maximum number of iterations of the k-means algorithm for a single\n        run.\n    tol: float, defaults = 1e-6\n        Relative tolerance with regards to Frobenius norm of the difference\n        in the cluster centers of two consecutive iterations to declare\n        convergence.\n    verbose: bool, defaults = False\n        Verbosity mode.\n    random_state: int or np.random.RandomState instance or None, defaults = None\n        Determines random number generation for centroid initialization.\n    distance_params: dict, defaults = None\n        Dictonary containing kwargs for the distance metric being used.\n\n    Attributes\n    ----------\n    cluster_centers_: np.ndarray (3d array of shape (n_clusters, n_dimensions,\n        series_length))\n        Time series that represent each of the cluster centers. If the algorithm stops\n        before fully converging these will not be consistent with labels_.\n    labels_: np.ndarray (1d array of shape (n_instance,))\n        Labels that is the index each time series belongs to.\n    inertia_: float\n        Sum of squared distances of samples to their closest cluster center, weighted by\n        the sample weights if provided.\n    n_iter_: int\n        Number of iterations run.\n    """\n\n    def __init__(\n        self,\n        n_clusters: int = 8,\n        init_algorithm: Union[str, Callable] = "random",\n        metric: Union[str, Callable] = "dtw",\n        n_init: int = 10,\n        max_iter: int = 300,\n        tol: float = 1e-6,\n        verbose: bool = False,\n        random_state: Union[int, RandomState] = None,\n        distance_params: dict = None,\n    ):\n        self._precomputed_pairwise = None\n\n        super(TimeSeriesKMedoids, self).__init__(\n            n_clusters,\n            init_algorithm,\n            metric,\n            n_init,\n            max_iter,\n            tol,\n            verbose,\n            random_state,\n            distance_params,\n        )\n\n    def _fit(self, X: np.ndarray, y=None) -> np.ndarray:\n        """Fit time series clusterer to training data.\n\n        Parameters\n        ----------\n        X : np.ndarray (2d or 3d array of shape (n_instances, series_length) or shape\n            (n_instances, n_dimensions, series_length))\n            Training time series instances to cluster.\n        y: ignored, exists for API consistency reasons.\n\n        Returns\n        -------\n        self:\n            Fitted estimator.\n        """\n        self._check_params(X)\n        self._precomputed_pairwise = pairwise_distance(\n            X, metric=self.metric, **self._distance_params\n        )\n        return super()._fit(X, y)\n\n    def _compute_new_cluster_centers(\n        self, X: np.ndarray, assignment_indexes: np.ndarray\n    ) -> np.ndarray:\n        """Compute new centers.\n\n        Parameters\n        ----------\n        X : np.ndarray (3d array of shape (n_instances, n_dimensions, series_length))\n            Time series instances to predict their cluster indexes.\n        assignment_indexes: np.ndarray\n            Indexes that each time series in X belongs to.\n\n        Returns\n        -------\n        np.ndarray (3d of shape (n_clusters, n_dimensions, series_length)\n            New cluster center values.\n        """\n        new_centers = np.zeros((self.n_clusters, X.shape[1], X.shape[2]))\n        for i in range(self.n_clusters):\n            curr_indexes = np.where(assignment_indexes == i)[0]\n            distance_matrix = np.zeros((len(curr_indexes), len(curr_indexes)))\n            for j in range(len(curr_indexes)):\n                for k in range(len(curr_indexes)):\n                    distance_matrix[j, k] = self._precomputed_pairwise[j, k]\n            result = medoids(X[curr_indexes], self._precomputed_pairwise)\n            if result.shape[0] > 0:\n                new_centers[i, :] = result\n        return new_centers\n\n    @classmethod\n    def get_test_params(cls, parameter_set="default"):\n        """Return testing parameter settings for the estimator.\n\n        Parameters\n        ----------\n        parameter_set : str, default="default"\n            Name of the set of test parameters to return, for use in tests. If no\n            special parameters are defined for a value, will return `"default"` set.\n\n\n        Returns\n        -------\n        params : dict or list of dict, default = {}\n            Parameters to create testing instances of the class\n            Each dict are parameters to construct an "interesting" test instance, i.e.,\n            `MyClass(**params)` or `MyClass(**params[i])` creates a valid test instance.\n            `create_test_instance` uses the first (or only) dictionary in `params`\n        """\n        params = {\n            "n_clusters": 2,\n            "init_algorithm": "random",\n            "metric": "euclidean",\n            "n_init": 1,\n            "max_iter": 1,\n            "tol": 1e-4,\n            "verbose": False,\n            "random_state": 1,\n        }\n        return params\n',
            'sktime/clustering/tests/test_k_medoids.py': '# -*- coding: utf-8 -*-\n"""Tests for time series k-medoids."""\nimport numpy as np\nfrom sklearn import metrics\n\nfrom sktime.clustering.k_medoids import TimeSeriesKMedoids\nfrom sktime.datasets import load_basic_motions\n\nexpected_results = {\n    "medoids": [\n        0,\n        0,\n        0,\n        0,\n        0,\n        0,\n        0,\n        0,\n        0,\n        0,\n        4,\n        0,\n        3,\n        0,\n        0,\n        0,\n        5,\n        0,\n        0,\n        0,\n        0,\n        0,\n        0,\n        0,\n        0,\n        0,\n        0,\n        0,\n        0,\n        0,\n        0,\n        0,\n        0,\n        0,\n        0,\n        0,\n        0,\n        0,\n        0,\n        0,\n    ]\n}\n\nexpected_score = {"medoids": 0.3153846153846154}\n\ntrain_expected_score = {"medoids": 0.4858974358974359}\n\nexpected_inertia = {"medoids": 2387.3342740600688}\n\nexpected_iters = {"medoids": 5}\n\nexpected_labels = {\n    "medoids": [\n        0,\n        0,\n        0,\n        0,\n        0,\n        0,\n        0,\n        0,\n        0,\n        0,\n        3,\n        0,\n        0,\n        5,\n        2,\n        4,\n        1,\n        0,\n        1,\n        4,\n        0,\n        0,\n        0,\n        0,\n        0,\n        0,\n        0,\n        0,\n        0,\n        0,\n        7,\n        0,\n        0,\n        6,\n        0,\n        0,\n        0,\n        0,\n        0,\n        0,\n    ]\n}\n\n\ndef test_kmedoids():\n    """Test implementation of Kmedoids."""\n    X_train, y_train = load_basic_motions(split="train")\n    X_test, y_test = load_basic_motions(split="test")\n\n    kmedoids = TimeSeriesKMedoids(\n        random_state=1,\n        n_init=2,\n        max_iter=5,\n        init_algorithm="kmeans++",\n        metric="euclidean",\n    )\n    train_predict = kmedoids.fit_predict(X_train)\n    train_score = metrics.rand_score(y_train, train_predict)\n    test_medoids_result = kmedoids.predict(X_test)\n    medoids_score = metrics.rand_score(y_test, test_medoids_result)\n    proba = kmedoids.predict_proba(X_test)\n\n    assert np.array_equal(test_medoids_result, expected_results["medoids"])\n    assert medoids_score == expected_score["medoids"]\n    assert train_score == train_expected_score["medoids"]\n    assert np.isclose(kmedoids.inertia_, expected_inertia["medoids"])\n    assert kmedoids.n_iter_ == expected_iters["medoids"]\n    assert np.array_equal(kmedoids.labels_, expected_labels["medoids"])\n    assert isinstance(kmedoids.cluster_centers_, np.ndarray)\n    assert proba.shape == (40, 8)\n\n    for val in proba:\n        assert np.count_nonzero(val == 1.0) == 1\n',
        }
