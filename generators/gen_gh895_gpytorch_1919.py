"""
Parameterized generator for GH895_gpytorch_1919.

Source PR:    https://github.com/cornellius-gp/gpytorch/pull/1919
Source Issue: https://github.com/cornellius-gp/gpytorch/issues/1915

Seed varies: renames 'active_dims' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH895_gpytorch_1919'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH895_gpytorch_1919'
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
                files[fpath] = files[fpath].replace('active_dims', 'active_dims' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH895_gpytorch_1919',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'cornellius-gp/gpytorch',
                "pr_number": 1919,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/cornellius-gp/gpytorch/pull/1919",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'gpytorch/kernels/periodic_kernel.py': '#!/usr/bin/env python3\n\nimport math\nfrom typing import Optional\n\nimport torch\n\nfrom ..constraints import Interval, Positive\nfrom ..priors import Prior\nfrom .kernel import Kernel\n\n\nclass PeriodicKernel(Kernel):\n    r"""Computes a covariance matrix based on the periodic kernel\n    between inputs :math:`\\mathbf{x_1}` and :math:`\\mathbf{x_2}`:\n\n    .. math::\n\n        \\begin{equation*}\n            k_{\\text{Periodic}}(\\mathbf{x_1}, \\mathbf{x_2}) = \\exp \\left(\n            -2 \\sum_i\n            \\frac{\\sin ^2 \\left( \\frac{\\pi}{p} (\\mathbf{x_{1,i}} - \\mathbf{x_{2,i}} ) \\right)}{\\lambda}\n            \\right)\n        \\end{equation*}\n\n    where\n\n    * :math:`p` is the period length parameter.\n    * :math:`\\lambda` is a lengthscale parameter.\n\n    Equation is based on [David Mackay\'s Introduction to Gaussian Processes equation 47]\n    (http://citeseerx.ist.psu.edu/viewdoc/download?doi=10.1.1.81.1927&rep=rep1&type=pdf)\n    albeit without feature-specific lengthscales and period lengths. The exponential\n    coefficient was changed and lengthscale is not squared to maintain backwards compatibility\n\n    .. note::\n\n        This kernel does not have an `outputscale` parameter. To add a scaling parameter,\n        decorate this kernel with a :class:`gpytorch.kernels.ScaleKernel`.\n\n    .. note::\n\n        This kernel does not have an ARD lengthscale or period length option.\n\n    Args:\n        :attr:`batch_shape` (torch.Size, optional):\n            Set this if you want a separate lengthscale for each\n             batch of input data. It should be `b` if :attr:`x1` is a `b x n x d` tensor. Default: `torch.Size([])`.\n        :attr:`active_dims` (tuple of ints, optional):\n            Set this if you want to compute the covariance of only a few input dimensions. The ints\n            corresponds to the indices of the dimensions. Default: `None`.\n        :attr:`period_length_prior` (Prior, optional):\n            Set this if you want to apply a prior to the period length parameter.  Default: `None`.\n        :attr:`lengthscale_prior` (Prior, optional):\n            Set this if you want to apply a prior to the lengthscale parameter.  Default: `None`.\n        :attr:`lengthscale_constraint` (Constraint, optional):\n            Set this if you want to apply a constraint to the value of the lengthscale. Default: `Positive`.\n        :attr:`period_length_constraint` (Constraint, optional):\n            Set this if you want to apply a constraint to the value of the period length. Default: `Positive`.\n        :attr:`eps` (float):\n            The minimum value that the lengthscale/period length can take\n            (prevents divide by zero errors). Default: `1e-6`.\n\n    Attributes:\n        :attr:`lengthscale` (Tensor):\n            The lengthscale parameter. Size = `*batch_shape x 1 x 1`.\n        :attr:`period_length` (Tensor):\n            The period length parameter. Size = `*batch_shape x 1 x 1`.\n\n    Example:\n        >>> x = torch.randn(10, 5)\n        >>> # Non-batch: Simple option\n        >>> covar_module = gpytorch.kernels.ScaleKernel(gpytorch.kernels.PeriodicKernel())\n        >>>\n        >>> batch_x = torch.randn(2, 10, 5)\n        >>> # Batch: Simple option\n        >>> covar_module = gpytorch.kernels.ScaleKernel(gpytorch.kernels.PeriodicKernel())\n        >>> # Batch: different lengthscale for each batch\n        >>> covar_module = gpytorch.kernels.ScaleKernel(gpytorch.kernels.PeriodicKernel(batch_size=2))\n        >>> covar = covar_module(x)  # Output: LazyVariable of size (2 x 10 x 10)\n    """\n\n    has_lengthscale = True\n\n    def __init__(\n        self,\n        period_length_prior: Optional[Prior] = None,\n        period_length_constraint: Optional[Interval] = None,\n        **kwargs,\n    ):\n        super(PeriodicKernel, self).__init__(**kwargs)\n        if period_length_constraint is None:\n            period_length_constraint = Positive()\n\n        self.register_parameter(\n            name="raw_period_length", parameter=torch.nn.Parameter(torch.zeros(*self.batch_shape, 1, 1))\n        )\n\n        if period_length_prior is not None:\n            if not isinstance(period_length_prior, Prior):\n                raise TypeError("Expected gpytorch.priors.Prior but got " + type(period_length_prior).__name__)\n            self.register_prior(\n                "period_length_prior",\n                period_length_prior,\n                lambda m: m.period_length,\n                lambda m, v: m._set_period_length(v),\n            )\n\n        self.register_constraint("raw_period_length", period_length_constraint)\n\n    @property\n    def period_length(self):\n        return self.raw_period_length_constraint.transform(self.raw_period_length)\n\n    @period_length.setter\n    def period_length(self, value):\n        self._set_period_length(value)\n\n    def _set_period_length(self, value):\n        if not torch.is_tensor(value):\n            value = torch.as_tensor(value).to(self.raw_period_length)\n        self.initialize(raw_period_length=self.raw_period_length_constraint.inverse_transform(value))\n\n    def forward(self, x1, x2, diag=False, **params):\n        x1_ = x1.div(self.period_length).mul(math.pi)\n        x2_ = x2.div(self.period_length).mul(math.pi)\n        diff = x1_.unsqueeze(-2) - x2_.unsqueeze(-3)\n        res = diff.sin().pow(2).sum(dim=-1).div(self.lengthscale).mul(-2.0).exp_()\n        if diag:\n            res = res.squeeze(0)\n        return res\n',
            'test/kernels/test_periodic_kernel.py': '#!/usr/bin/env python3\n\nimport math\nimport unittest\n\nimport torch\n\nfrom gpytorch.kernels import PeriodicKernel\nfrom gpytorch.priors import NormalPrior\n\n\nclass TestPeriodicKernel(unittest.TestCase):\n    def test_computes_periodic_function(self):\n        a = torch.tensor([4, 2, 8], dtype=torch.float).view(3, 1)\n        b = torch.tensor([0, 2], dtype=torch.float).view(2, 1)\n        lengthscale = 2\n        period = 3\n        kernel = PeriodicKernel().initialize(lengthscale=lengthscale, period_length=period)\n        kernel.eval()\n\n        actual = torch.zeros(3, 2)\n        for i in range(3):\n            for j in range(2):\n                val = 2 * torch.pow(torch.sin(math.pi * (a[i] - b[j]) / 3), 2) / lengthscale\n                actual[i, j] = torch.exp(-val).item()\n\n        res = kernel(a, b).evaluate()\n        self.assertLess(torch.norm(res - actual), 1e-5)\n\n    def test_is_pd(self):\n        # ensures 1d input is positive definite with additional jitter\n        x = torch.randn(100).reshape(-1, 1)\n        kernel = PeriodicKernel()\n        with torch.no_grad():\n            K = kernel(x, x).evaluate() + 1e-4 * torch.eye(len(x))\n            eig = torch.linalg.eigvalsh(K)\n            self.assertTrue((eig > 0.0).all().item())\n\n    def test_multidimensional_inputs(self):\n        # test taken from issue #835\n        # ensures multidimensional input results in a positive definite kernel matrix, with additional jitter\n        x = torch.randn(1000, 2)\n        kernel = PeriodicKernel()\n        with torch.no_grad():\n            K = kernel(x, x).evaluate() + 1e-4 * torch.eye(len(x))\n            eig = torch.linalg.eigvalsh(K)\n            self.assertTrue((eig > 0.0).all().item())\n\n    def test_batch(self):\n        a = torch.tensor([[4, 2, 8], [1, 2, 3]], dtype=torch.float).view(2, 3, 1)\n        b = torch.tensor([[0, 2], [-1, 2]], dtype=torch.float).view(2, 2, 1)\n        period = torch.tensor(1, dtype=torch.float).view(1, 1, 1)\n        lengthscale = torch.tensor(2, dtype=torch.float).view(1, 1, 1)\n        kernel = PeriodicKernel().initialize(lengthscale=lengthscale, period_length=period)\n        kernel.eval()\n\n        actual = torch.zeros(2, 3, 2)\n        for k in range(2):\n            actual[k] = kernel(a[k], b[k]).evaluate()\n\n        res = kernel(a, b).evaluate()\n        self.assertLess(torch.norm(res - actual), 1e-5)\n\n    def test_batch_separate(self):\n        a = torch.tensor([[4, 2, 8], [1, 2, 3]], dtype=torch.float).view(2, 3, 1)\n        b = torch.tensor([[0, 2], [-1, 2]], dtype=torch.float).view(2, 2, 1)\n        period = torch.tensor([1, 2], dtype=torch.float).view(2, 1, 1)\n        lengthscale = torch.tensor([2, 1], dtype=torch.float).view(2, 1, 1)\n        kernel = PeriodicKernel(batch_shape=torch.Size([2])).initialize(lengthscale=lengthscale, period_length=period)\n        kernel.eval()\n\n        actual = torch.zeros(2, 3, 2)\n        for k in range(2):\n            diff = a[k].unsqueeze(1) - b[k].unsqueeze(0)\n            diff = diff * math.pi / period[k].unsqueeze(-1)\n            actual[k] = diff.sin().pow(2).sum(dim=-1).div(lengthscale[k]).mul(-2.0).exp_()\n\n        res = kernel(a, b).evaluate()\n        self.assertLess(torch.norm(res - actual), 1e-5)\n\n    def create_kernel_with_prior(self, period_length_prior):\n        return PeriodicKernel(period_length_prior=period_length_prior)\n\n    def test_prior_type(self):\n        """\n        Raising TypeError if prior type is other than gpytorch.priors.Prior\n        """\n        kernel_fn = lambda prior: self.create_kernel_with_prior(prior)\n        kernel_fn(None)\n        kernel_fn(NormalPrior(0, 1))\n        self.assertRaises(TypeError, kernel_fn, 1)\n\n\nif __name__ == "__main__":\n    unittest.main()\n',
        }
