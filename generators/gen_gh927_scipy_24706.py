"""
Parameterized generator for GH927_scipy_24706.

Source PR:    https://github.com/scipy/scipy/pull/24706
Source Issue: N/A

Seed varies: renames 'array' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH927_scipy_24706'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH927_scipy_24706'
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
                files[fpath] = files[fpath].replace('array', 'array' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH927_scipy_24706',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'scipy/scipy',
                "pr_number": 24706,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/scipy/scipy/pull/24706",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'scipy/sparse/csgraph/_validation.py': 'import numpy as np\nfrom scipy.sparse import issparse\nfrom scipy.sparse._sputils import convert_pydata_sparse_to_scipy\nfrom scipy.sparse.csgraph._tools import (\n    csgraph_to_dense, csgraph_from_dense,\n    csgraph_masked_from_dense, csgraph_from_masked\n)\n\nDTYPE = np.float64\n\n\ndef validate_graph(csgraph, directed, dtype=DTYPE,\n                   csr_output=True, dense_output=True,\n                   copy_if_dense=False, copy_if_sparse=False,\n                   null_value_in=0, null_value_out=np.inf,\n                   infinity_null=True, nan_null=True):\n    """Routine for validation and conversion of csgraph inputs"""\n    if not (csr_output or dense_output):\n        raise ValueError("Internal: dense or csr output must be true")\n\n    accept_fv = [null_value_in]\n    if infinity_null:\n        accept_fv.append(np.inf)\n    if nan_null:\n        accept_fv.append(np.nan)\n    csgraph = convert_pydata_sparse_to_scipy(csgraph, accept_fv=accept_fv)\n\n    # if undirected and csc storage, then transposing in-place\n    # is quicker than later converting to csr.\n    if (not directed) and issparse(csgraph) and csgraph.format == "csc":\n        csgraph = csgraph.T\n\n    if issparse(csgraph):\n        if csr_output:\n            csgraph = csgraph.tocsr(copy=copy_if_sparse).astype(DTYPE, copy=False)\n        else:\n            csgraph = csgraph_to_dense(csgraph, null_value=null_value_out)\n    elif np.ma.isMaskedArray(csgraph):\n        if dense_output:\n            mask = csgraph.mask\n            csgraph = np.array(csgraph.data, dtype=DTYPE, copy=copy_if_dense)\n            csgraph[mask] = null_value_out\n        else:\n            csgraph = csgraph_from_masked(csgraph)\n    else:\n        if dense_output:\n            csgraph = csgraph_masked_from_dense(csgraph,\n                                                copy=copy_if_dense,\n                                                null_value=null_value_in,\n                                                nan_null=nan_null,\n                                                infinity_null=infinity_null)\n            mask = csgraph.mask\n            csgraph = np.asarray(csgraph.data, dtype=DTYPE)\n            csgraph[mask] = null_value_out\n        else:\n            csgraph = csgraph_from_dense(csgraph, null_value=null_value_in,\n                                         infinity_null=infinity_null,\n                                         nan_null=nan_null)\n\n    if csgraph.ndim != 2:\n        raise ValueError("compressed-sparse graph must be 2-D")\n\n    if csgraph.shape[0] != csgraph.shape[1]:\n        raise ValueError("compressed-sparse graph must be shape (N, N)")\n\n    return csgraph\n',
            'scipy/sparse/csgraph/tests/test_connected_components.py': "import numpy as np\nfrom numpy.testing import assert_equal, assert_array_almost_equal\nfrom scipy.sparse import csgraph, csr_array\n\n\ndef test_weak_connections():\n    Xde = np.array([[0, 1, 0],\n                    [0, 0, 0],\n                    [0, 0, 0]])\n\n    Xsp = csgraph.csgraph_from_dense(Xde, null_value=0)\n\n    for X in Xsp, Xde:\n        n_components, labels =\\\n            csgraph.connected_components(X, directed=True,\n                                         connection='weak')\n\n        assert_equal(n_components, 2)\n        assert_array_almost_equal(labels, [0, 0, 1])\n\n\ndef test_strong_connections():\n    X1de = np.array([[0, 1, 0],\n                     [0, 0, 0],\n                     [0, 0, 0]])\n    X2de = X1de + X1de.T\n\n    X1sp = csgraph.csgraph_from_dense(X1de, null_value=0)\n    X2sp = csgraph.csgraph_from_dense(X2de, null_value=0)\n\n    for X in X1sp, X1de:\n        n_components, labels =\\\n            csgraph.connected_components(X, directed=True,\n                                         connection='strong')\n\n        assert_equal(n_components, 3)\n        labels.sort()\n        assert_array_almost_equal(labels, [0, 1, 2])\n\n    for X in X2sp, X2de:\n        n_components, labels =\\\n            csgraph.connected_components(X, directed=True,\n                                         connection='strong')\n\n        assert_equal(n_components, 2)\n        labels.sort()\n        assert_array_almost_equal(labels, [0, 0, 1])\n\n\ndef test_strong_connections2():\n    X = np.array([[0, 0, 0, 0, 0, 0],\n                  [1, 0, 1, 0, 0, 0],\n                  [0, 0, 0, 1, 0, 0],\n                  [0, 0, 1, 0, 1, 0],\n                  [0, 0, 0, 0, 0, 0],\n                  [0, 0, 0, 0, 1, 0]])\n    n_components, labels =\\\n        csgraph.connected_components(X, directed=True,\n                                     connection='strong')\n    assert_equal(n_components, 5)\n    labels.sort()\n    assert_array_almost_equal(labels, [0, 1, 2, 2, 3, 4])\n\n\ndef test_weak_connections2():\n    X = np.array([[0, 0, 0, 0, 0, 0],\n                  [1, 0, 0, 0, 0, 0],\n                  [0, 0, 0, 1, 0, 0],\n                  [0, 0, 1, 0, 1, 0],\n                  [0, 0, 0, 0, 0, 0],\n                  [0, 0, 0, 0, 1, 0]])\n    n_components, labels =\\\n        csgraph.connected_components(X, directed=True,\n                                     connection='weak')\n    assert_equal(n_components, 2)\n    labels.sort()\n    assert_array_almost_equal(labels, [0, 0, 1, 1, 1, 1])\n\n\ndef test_ticket1876():\n    # Regression test: this failed in the original implementation\n    # There should be two strongly-connected components; previously gave one\n    g = np.array([[0, 1, 1, 0],\n                  [1, 0, 0, 1],\n                  [0, 0, 0, 1],\n                  [0, 0, 1, 0]])\n    n_components, labels = csgraph.connected_components(g, connection='strong')\n\n    assert_equal(n_components, 2)\n    assert_equal(labels[0], labels[1])\n    assert_equal(labels[2], labels[3])\n\n\ndef test_fully_connected_graph():\n    # Fully connected dense matrices raised an exception.\n    # https://github.com/scipy/scipy/issues/3818\n    g = np.ones((4, 4))\n    n_components, labels = csgraph.connected_components(g)\n    assert_equal(n_components, 1)\n\n\ndef test_int64_indices_undirected():\n    # See https://github.com/scipy/scipy/issues/18716\n    g = csr_array(([1], np.array([[0], [1]], dtype=np.int64)), shape=(2, 2))\n    assert g.indices.dtype == np.int64\n    n, labels = csgraph.connected_components(g, directed=False)\n    assert n == 1\n    assert_array_almost_equal(labels, [0, 0])\n\n\ndef test_int64_indices_directed():\n    # See https://github.com/scipy/scipy/issues/18716\n    g = csr_array(([1], np.array([[0], [1]], dtype=np.int64)), shape=(2, 2))\n    assert g.indices.dtype == np.int64\n    n, labels = csgraph.connected_components(g, directed=True,\n                                             connection='strong')\n    assert n == 2\n    assert_array_almost_equal(labels, [1, 0])\n\n",
        }
