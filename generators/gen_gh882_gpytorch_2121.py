"""
Parameterized generator for GH882_gpytorch_2121.

Source PR:    https://github.com/cornellius-gp/gpytorch/pull/2121
Source Issue: https://github.com/cornellius-gp/gpytorch/issues/2113

Seed varies: renames 'abstractmethod' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH882_gpytorch_2121'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH882_gpytorch_2121'
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
                files[fpath] = files[fpath].replace('abstractmethod', 'abstractmethod' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH882_gpytorch_2121',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'cornellius-gp/gpytorch',
                "pr_number": 2121,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/cornellius-gp/gpytorch/pull/2121",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'docs/source/marginal_log_likelihoods.rst': '.. role:: hidden\n    :class: hidden-section\n\ngpytorch.mlls\n===================================\n\nThese are modules to compute (or approximate/bound) the marginal log likelihood\n(MLL) of the GP model when applied to data.  I.e., given a GP :math:`f \\sim\n\\mathcal{GP}(\\mu, K)`, and data :math:`\\mathbf X, \\mathbf y`, these modules\ncompute/approximate\n\n.. math::\n\n   \\begin{equation*}\n      \\mathcal{L} = p_f(\\mathbf y \\! \\mid \\! \\mathbf X)\n      = \\int p \\left( \\mathbf y \\! \\mid \\! f(\\mathbf X) \\right) \\: p(f(\\mathbf X) \\! \\mid \\! \\mathbf X) \\: d f\n   \\end{equation*}\n\nThis is computed exactly when the GP inference is computed exactly (e.g. regression w/ a Gaussian likelihood).\nIt is approximated/bounded for GP models that use approximate inference.\n\nThese models are typically used as the "loss" functions for GP models (though note that the output of\nthese functions must be negated for optimization).\n\n.. automodule:: gpytorch.mlls\n.. currentmodule:: gpytorch.mlls\n\n\nExact GP Inference\n-----------------------------\n\nThese are MLLs for use with :obj:`~gpytorch.models.ExactGP` modules. They compute the MLL exactly.\n\n:hidden:`ExactMarginalLogLikelihood`\n~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n\n.. autoclass:: ExactMarginalLogLikelihood\n   :members:\n\n:hidden:`LeaveOneOutPseudoLikelihood`\n~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n\n.. autoclass:: LeaveOneOutPseudoLikelihood\n   :members:\n\nApproximate GP Inference\n-----------------------------------\n\nThese are MLLs for use with :obj:`~gpytorch.models.ApproximateGP` modules. They are designed for\nwhen exact inference is intractable (either when the likelihood is non-Gaussian likelihood, or when\nthere is too much data for an ExactGP model).\n\n:hidden:`VariationalELBO`\n~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n\n.. autoclass:: VariationalELBO\n   :members:\n\n:hidden:`PredictiveLogLikelihood`\n~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n\n.. autoclass:: PredictiveLogLikelihood\n   :members:\n\n:hidden:`GammaRobustVariationalELBO`\n~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n\n.. autoclass:: GammaRobustVariationalELBO\n   :members:\n\n:hidden:`DeepApproximateMLL`\n~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n\n.. autoclass:: DeepApproximateMLL\n   :members:\n',
            'gpytorch/mlls/added_loss_term.py': '#!/usr/bin/env python3\n\n\nclass AddedLossTerm(object):\n    def loss(self):\n        raise NotImplementedError\n',
            'gpytorch/mlls/inducing_point_kernel_added_loss_term.py': '#!/usr/bin/env python3\n\nfrom .added_loss_term import AddedLossTerm\n\n\nclass InducingPointKernelAddedLossTerm(AddedLossTerm):\n    def __init__(self, prior_dist, variational_dist, likelihood):\n        self.prior_dist = prior_dist\n        self.variational_dist = variational_dist\n        self.likelihood = likelihood\n\n    def loss(self, *params):\n        prior_covar = self.prior_dist.lazy_covariance_matrix\n        variational_covar = self.variational_dist.lazy_covariance_matrix\n        diag = prior_covar.diagonal(dim1=-1, dim2=-2) - variational_covar.diagonal(dim1=-1, dim2=-2)\n        shape = prior_covar.shape[:-1]\n        noise_diag = self.likelihood._shaped_noise_covar(shape, *params).diagonal(dim1=-1, dim2=-2)\n        return -0.5 * (diag / noise_diag).sum()\n',
            'gpytorch/mlls/kl_gaussian_added_loss_term.py': '#!/usr/bin/env python3\n\nfrom torch.distributions import kl_divergence\n\nfrom .added_loss_term import AddedLossTerm\n\n\nclass KLGaussianAddedLossTerm(AddedLossTerm):\n    def __init__(self, q_x, p_x, n, data_dim):\n        super().__init__()\n        self.q_x = q_x\n        self.p_x = p_x\n        self.n = n\n        self.data_dim = data_dim\n\n    def loss(self):\n        kl_per_latent_dim = kl_divergence(self.q_x, self.p_x).sum(axis=0)  # vector of size latent_dim\n        kl_per_point = kl_per_latent_dim.sum() / self.n  # scalar\n        # inside the forward method of variational ELBO,\n        # the added loss terms are expanded (using add_) to take the same\n        # shape as the log_lik term (has shape data_dim)\n        # so they can be added together. Hence, we divide by data_dim to avoid\n        # overcounting the kl term\n        return kl_per_point / self.data_dim\n',
            'test/examples/test_kronecker_multitask_sgpr_regression.py': '#!/usr/bin/env python3\n\nfrom math import pi\n\nimport torch\nimport unittest\n\nimport gpytorch\nfrom gpytorch.means import ConstantMean, MultitaskMean\nfrom gpytorch.likelihoods import MultitaskGaussianLikelihood\nfrom gpytorch.distributions import MultitaskMultivariateNormal\nfrom gpytorch.test.base_test_case import BaseTestCase\n\n\n# Simple training data: let\'s try to learn a sine function\ntrain_x = torch.linspace(0, 1, 100)\n\n# y1 function is sin(2*pi*x) with noise N(0, 0.04)\ntrain_y1 = torch.sin(train_x * (2 * pi)) + torch.randn(train_x.size()) * 0.1\n# y2 function is cos(2*pi*x) with noise N(0, 0.04)\ntrain_y2 = torch.cos(train_x * (2 * pi)) + torch.randn(train_x.size()) * 0.1\n\n# Create a train_y which interleaves the two\ntrain_y = torch.stack([train_y1, train_y2], -1)\n\n\nclass MultitaskGPModel(gpytorch.models.ExactGP):\n    def __init__(self, train_x, train_y, likelihood):\n        super(MultitaskGPModel, self).__init__(train_x, train_y, likelihood)\n        self.mean_module = MultitaskMean(ConstantMean(), num_tasks=2)\n        self.covar_module = gpytorch.kernels.MultitaskKernel(\n            gpytorch.kernels.InducingPointKernel(\n                gpytorch.kernels.RBFKernel(), inducing_points=torch.randn(50, 1), likelihood=likelihood\n            ), num_tasks=2, rank=2\n        )\n\n    def forward(self, x):\n        mean_x = self.mean_module(x)\n        covar_x = self.covar_module(x)\n        return MultitaskMultivariateNormal(mean_x, covar_x)\n\n\nclass TestSimpleGPRegression(BaseTestCase, unittest.TestCase):\n    seed = 0\n\n    def test_multitask_gp_mean_abs_error(self):\n        likelihood = MultitaskGaussianLikelihood(num_tasks=2)\n        model = MultitaskGPModel(train_x, train_y, likelihood)\n        # Find optimal model hyperparameters\n        model.train()\n        likelihood.train()\n\n        # Use the adam optimizer\n        optimizer = torch.optim.Adam(model.parameters(), lr=0.1)  # Includes GaussianLikelihood parameters\n\n        # "Loss" for GPs - the marginal log likelihood\n        mll = gpytorch.mlls.ExactMarginalLogLikelihood(likelihood, model)\n\n        n_iter = 50\n        for _ in range(n_iter):\n            # Zero prev backpropped gradients\n            optimizer.zero_grad()\n            # Make predictions from training data\n            # Again, note feeding duplicated x_data and indices indicating which task\n            output = model(train_x)\n            # TODO: Fix this view call!!\n            loss = -mll(output, train_y)\n            loss.backward()\n            optimizer.step()\n\n        # Test the model\n        model.eval()\n        likelihood.eval()\n        test_x = torch.linspace(0, 1, 51)\n        test_y1 = torch.sin(test_x * (2 * pi))\n        test_y2 = torch.cos(test_x * (2 * pi))\n        test_preds = likelihood(model(test_x)).mean\n        mean_abs_error_task_1 = torch.mean(torch.abs(test_y1 - test_preds[:, 0]))\n        mean_abs_error_task_2 = torch.mean(torch.abs(test_y2 - test_preds[:, 1]))\n\n        self.assertLess(mean_abs_error_task_1.squeeze().item(), 0.05)\n        self.assertLess(mean_abs_error_task_2.squeeze().item(), 0.05)\n\n\nif __name__ == "__main__":\n    unittest.main()\n',
            'test/mlls/test_inducing_point_kernel_added_loss_term.py': '#!/usr/bin/env python3\n\nimport unittest\n\nimport torch\nfrom linear_operator.operators import DiagLinearOperator\n\nfrom gpytorch.distributions import MultivariateNormal\nfrom gpytorch.likelihoods import GaussianLikelihood\nfrom gpytorch.mlls import InducingPointKernelAddedLossTerm\nfrom gpytorch.test.base_test_case import BaseTestCase\n\n\nclass TestInducingPointKernelAddedLossTerm(BaseTestCase, unittest.TestCase):\n    def test_added_loss_term(self):\n        # This loss term won\'t usually be called with diagonal MVNs\n        # However, the loss term only accesses the diagonals of the MVN covariance matrices\n        # So we\'re simplifying the setup for the unit test\n        prior_dist = MultivariateNormal(torch.zeros(5), DiagLinearOperator(torch.tensor([1.0, 1.0, 1.0, 1.0, 1.0])))\n        variational_dist = MultivariateNormal(\n            torch.zeros(5), DiagLinearOperator(torch.tensor([0.6, 0.7, 0.8, 0.9, 1.0]))\n        )\n        likelihood = GaussianLikelihood()\n        likelihood.noise = 0.01\n\n        added_loss_term = InducingPointKernelAddedLossTerm(prior_dist, variational_dist, likelihood)\n        self.assertAllClose(added_loss_term.loss(), torch.tensor(-50.0))\n\n    def test_added_loss_term_batch(self):\n        prior_dist = MultivariateNormal(\n            torch.zeros(2, 5), DiagLinearOperator(torch.tensor([[1.0, 1.0, 1.0, 1.0, 1.0], [1.0, 1.0, 1.0, 1.0, 1.0]]))\n        )\n        variational_dist = MultivariateNormal(\n            torch.zeros(2, 5),\n            DiagLinearOperator(torch.tensor([[0.6, 0.7, 0.8, 0.9, 1.0], [0.8, 0.85, 0.9, 0.95, 1.0]])),\n        )\n        likelihood = GaussianLikelihood(batch_shape=torch.Size([3, 1]))\n        likelihood.noise = torch.Tensor([[0.01], [0.1], [1.0]])\n\n        added_loss_term = InducingPointKernelAddedLossTerm(prior_dist, variational_dist, likelihood)\n        self.assertAllClose(added_loss_term.loss(), torch.tensor([[-50.0, -25.0], [-5.0, -2.5], [-0.5, -0.25]]))\n\n\nif __name__ == "__main__":\n    unittest.main()\n',
        }
