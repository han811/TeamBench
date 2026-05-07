"""
Parameterized generator for GH1038_gpytorch_1416.

Source PR:    https://github.com/cornellius-gp/gpytorch/pull/1416
Source Issue: https://github.com/cornellius-gp/gpytorch/issues/1300

Seed varies: renames 'add_' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH1038_gpytorch_1416'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH1038_gpytorch_1416'
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
                files[fpath] = files[fpath].replace('add_', 'add_' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH1038_gpytorch_1416',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'cornellius-gp/gpytorch',
                "pr_number": 1416,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/cornellius-gp/gpytorch/pull/1416",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'gpytorch/variational/natural_variational_distribution.py': '#!/usr/bin/env python3\n\nimport abc\n\nimport torch\n\nfrom ..distributions import MultivariateNormal\nfrom ..lazy import CholLazyTensor, TriangularLazyTensor\nfrom ._variational_distribution import _VariationalDistribution\n\n\nclass _NaturalVariationalDistribution(_VariationalDistribution, abc.ABC):\n    r"""Any :obj:`~gpytorch.variational._VariationalDistribution` which calculates\n    natural gradients with respect to its parameters.\n    """\n    pass\n\n\nclass NaturalVariationalDistribution(_NaturalVariationalDistribution):\n    r"""A multivariate normal :obj:`~gpytorch.variational._VariationalDistribution`,\n    parameterized by **natural** parameters.\n\n    .. note::\n       The :obj:`~gpytorch.variational.NaturalVariationalDistribution` can only\n       be used with :obj:`gpytorch.optim.NGD`, or other optimizers\n       that follow exactly the gradient direction. Failure to do so will cause\n       the natural matrix :math:`\\mathbf \\Theta_\\text{mat}` to stop being\n       positive definite, and a :obj:`~RuntimeError` will be raised.\n\n    .. seealso::\n        The `natural gradient descent tutorial\n        <examples/04_Variational_and_Approximate_GPs/Natural_Gradient_Descent.ipynb>`_\n        for use instructions.\n\n        The :obj:`~gpytorch.variational.TrilNaturalVariationalDistribution` for\n        a more numerically stable parameterization, at the cost of needing more\n        iterations to make variational regression converge.\n\n    :param int num_inducing_points: Size of the variational distribution. This implies that the variational mean\n        should be this size, and the variational covariance matrix should have this many rows and columns.\n    :param batch_shape: Specifies an optional batch size\n        for the variational parameters. This is useful for example when doing additive variational inference.\n    :type batch_shape: :obj:`torch.Size`, optional\n    :param float mean_init_std: (Default: 1e-3) Standard deviation of gaussian noise to add to the mean initialization.\n\n    """\n\n    def __init__(self, num_inducing_points, batch_shape=torch.Size([]), mean_init_std=1e-3, **kwargs):\n        super().__init__(num_inducing_points=num_inducing_points, batch_shape=batch_shape, mean_init_std=mean_init_std)\n        scaled_mean_init = torch.zeros(num_inducing_points)\n        neg_prec_init = torch.eye(num_inducing_points, num_inducing_points).mul(-0.5)\n        scaled_mean_init = scaled_mean_init.repeat(*batch_shape, 1)\n        neg_prec_init = neg_prec_init.repeat(*batch_shape, 1, 1)\n\n        # eta1 and eta2 parameterization of the variational distribution\n        self.register_parameter(name="natural_vec", parameter=torch.nn.Parameter(scaled_mean_init))\n        self.register_parameter(name="natural_mat", parameter=torch.nn.Parameter(neg_prec_init))\n\n    def forward(self):\n        mean, chol_covar = _NaturalToMuVarSqrt.apply(self.natural_vec, self.natural_mat)\n        res = MultivariateNormal(mean, CholLazyTensor(TriangularLazyTensor(chol_covar)))\n        return res\n\n    def initialize_variational_distribution(self, prior_dist):\n        prior_prec = prior_dist.covariance_matrix.inverse()\n        prior_mean = prior_dist.mean\n        noise = torch.randn_like(prior_mean).mul_(self.mean_init_std)\n\n        self.natural_vec.data.copy_((prior_prec @ prior_mean).add_(noise))\n        self.natural_mat.data.copy_(prior_prec.mul(-0.5))\n\n\ndef _triangular_inverse(A, upper=False):\n    eye = torch.eye(A.size(-1), dtype=A.dtype, device=A.device)\n    return eye.triangular_solve(A, upper=upper).solution\n\n\ndef _phi_for_cholesky_(A):\n    "Modifies A to be the phi function used in differentiating through Cholesky"\n    A.tril_().diagonal(offset=0, dim1=-2, dim2=-1).mul_(0.5)\n    return A\n\n\ndef _cholesky_backward(dout_dL, L, L_inverse):\n    # c.f. https://github.com/pytorch/pytorch/blob/25ba802ce4cbdeaebcad4a03cec8502f0de9b7b3/\n    #      tools/autograd/templates/Functions.cpp\n    A = L.transpose(-1, -2) @ dout_dL\n    phi = _phi_for_cholesky_(A)\n    grad_input = (L_inverse.transpose(-1, -2) @ phi) @ L_inverse\n    # Symmetrize gradient\n    return grad_input.add(grad_input.transpose(-1, -2)).mul_(0.5)\n\n\nclass _NaturalToMuVarSqrt(torch.autograd.Function):\n    @staticmethod\n    def _forward(nat_mean, nat_covar):\n        try:\n            L_inv = torch.cholesky(-2.0 * nat_covar, upper=False)\n        except RuntimeError as e:\n            if str(e).startswith("cholesky"):\n                raise RuntimeError(\n                    "Non-negative-definite natural covariance. You probably "\n                    "updated it using an optimizer other than gpytorch.optim.NGD (such as Adam). "\n                    "This is not supported."\n                )\n            else:\n                raise e\n        L = _triangular_inverse(L_inv, upper=False)\n        S = L.transpose(-1, -2) @ L\n        mu = (S @ nat_mean.unsqueeze(-1)).squeeze(-1)\n        # Two choleskys are annoying, but we don\'t have good support for a\n        # LazyTensor of form L.T @ L\n        return mu, torch.cholesky(S, upper=False)\n\n    @staticmethod\n    def forward(ctx, nat_mean, nat_covar):\n        mu, L = _NaturalToMuVarSqrt._forward(nat_mean, nat_covar)\n        ctx.save_for_backward(mu, L)\n        return mu, L\n\n    @staticmethod\n    def _backward(dout_dmu, dout_dL, mu, L, C):\n        """Calculate dout/d(eta1, eta2), which are:\n        eta1 = mu\n        eta2 = mu*mu^T + LL^T = mu*mu^T + Sigma\n\n        Thus:\n        dout/deta1 = dout/dmu + dout/dL dL/deta1\n        dout/deta2 = dout/dL dL/deta1\n\n        For L = chol(eta2 - eta1*eta1^T).\n        dout/dSigma = _cholesky_backward(dout/dL, L)\n        dout/deta2 = dout/dSigma\n        dSigma/deta1 = -2* (dout/dSigma) mu\n        """\n        dout_dSigma = _cholesky_backward(dout_dL, L, C)\n        dout_deta1 = dout_dmu - 2 * (dout_dSigma @ mu.unsqueeze(-1)).squeeze(-1)\n        return dout_deta1, dout_dSigma\n\n    @staticmethod\n    def backward(ctx, dout_dmu, dout_dL):\n        "Calculates the natural gradient with respect to nat_mean, nat_covar"\n        mu, L = ctx.saved_tensors\n        C = _triangular_inverse(L, upper=False)\n        return _NaturalToMuVarSqrt._backward(dout_dmu, dout_dL, mu, L, C)\n',
            'test/variational/test_variational_strategy.py': '#!/usr/bin/env python3\n\nimport unittest\n\nimport torch\n\nimport gpytorch\nfrom gpytorch.test.variational_test_case import VariationalTestCase\n\n\nclass TestVariationalGP(VariationalTestCase, unittest.TestCase):\n    @property\n    def batch_shape(self):\n        return torch.Size([])\n\n    @property\n    def distribution_cls(self):\n        return gpytorch.variational.CholeskyVariationalDistribution\n\n    @property\n    def mll_cls(self):\n        return gpytorch.mlls.VariationalELBO\n\n    @property\n    def strategy_cls(self):\n        return gpytorch.variational.VariationalStrategy\n\n    def test_training_iteration(self, *args, **kwargs):\n        cg_mock, cholesky_mock, ciq_mock = super().test_training_iteration(*args, **kwargs)\n        self.assertFalse(cg_mock.called)\n        self.assertEqual(cholesky_mock.call_count, 2)  # One for each forward pass\n        self.assertFalse(ciq_mock.called)\n\n    def test_eval_iteration(self, *args, **kwargs):\n        cg_mock, cholesky_mock, ciq_mock = super().test_eval_iteration(*args, **kwargs)\n        self.assertFalse(cg_mock.called)\n        self.assertEqual(cholesky_mock.call_count, 1)  # One to compute cache, that\'s it!\n        self.assertFalse(ciq_mock.called)\n\n\nclass TestPredictiveGP(TestVariationalGP):\n    @property\n    def mll_cls(self):\n        return gpytorch.mlls.PredictiveLogLikelihood\n\n\nclass TestRobustVGP(TestVariationalGP):\n    @property\n    def mll_cls(self):\n        return gpytorch.mlls.GammaRobustVariationalELBO\n\n\nclass TestMeanFieldVariationalGP(TestVariationalGP):\n    @property\n    def distribution_cls(self):\n        return gpytorch.variational.MeanFieldVariationalDistribution\n\n\nclass TestMeanFieldPredictiveGP(TestPredictiveGP):\n    @property\n    def distribution_cls(self):\n        return gpytorch.variational.MeanFieldVariationalDistribution\n\n\nclass TestMeanFieldRobustVGP(TestRobustVGP):\n    @property\n    def distribution_cls(self):\n        return gpytorch.variational.MeanFieldVariationalDistribution\n\n\nclass TestDeltaVariationalGP(TestVariationalGP):\n    @property\n    def distribution_cls(self):\n        return gpytorch.variational.DeltaVariationalDistribution\n\n\nclass TestDeltaPredictiveGP(TestPredictiveGP):\n    @property\n    def distribution_cls(self):\n        return gpytorch.variational.DeltaVariationalDistribution\n\n\nclass TestDeltaRobustVGP(TestRobustVGP):\n    @property\n    def distribution_cls(self):\n        return gpytorch.variational.DeltaVariationalDistribution\n\n\nif __name__ == "__main__":\n    unittest.main()\n',
        }
