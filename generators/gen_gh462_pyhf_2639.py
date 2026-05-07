"""
Parameterized generator for GH462_pyhf_2639.

Source PR:    https://github.com/scikit-hep/pyhf/pull/2639
Source Issue: https://github.com/scikit-hep/pyhf/issues/2622

Seed varies: renames 'argument' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH462_pyhf_2639'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH462_pyhf_2639'
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
                files[fpath] = files[fpath].replace('argument', 'argument' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH462_pyhf_2639',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'scikit-hep/pyhf',
                "pr_number": 2639,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/scikit-hep/pyhf/pull/2639",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'pyproject.toml': '[build-system]\nrequires = [\n    "hatchling>=1.13.0",\n    "hatch-vcs>=0.3.0",\n]\nbuild-backend = "hatchling.build"\n\n[project]\nname = "pyhf"\ndynamic = ["version"]\ndescription = "pure-Python HistFactory implementation with tensors and autodiff"\nreadme = "README.rst"\nlicense = "Apache-2.0"\nrequires-python = ">=3.9"\nauthors = [\n    { name = "Lukas Heinrich", email = "lukas.heinrich@cern.ch" },\n    { name = "Matthew Feickert", email = "matthew.feickert@cern.ch" },\n    { name = "Giordon Stark", email = "gstark@cern.ch" },\n]\nmaintainers = [ {name = "The Scikit-HEP admins", email = "scikit-hep-admins@googlegroups.com"} ]\nkeywords = [\n    "fitting",\n    "jax",\n    "numpy",\n    "physics",\n    "scipy",\n]\nclassifiers = [\n    "Development Status :: 4 - Beta",\n    "Environment :: WebAssembly :: Emscripten",\n    "Intended Audience :: Science/Research",\n    "Operating System :: OS Independent",\n    "Programming Language :: Python :: 3",\n    "Programming Language :: Python :: 3 :: Only",\n    "Programming Language :: Python :: 3.9",\n    "Programming Language :: Python :: 3.10",\n    "Programming Language :: Python :: 3.11",\n    "Programming Language :: Python :: 3.12",\n    "Programming Language :: Python :: 3.13",\n    "Programming Language :: Python :: Implementation :: CPython",\n    "Topic :: Scientific/Engineering",\n    "Topic :: Scientific/Engineering :: Physics",\n]\ndependencies = [\n    "click>=8.0.0",  # for console scripts\n    "jsonpatch>=1.15",\n    "jsonschema>=4.15.0",  # for utils\n    "pyyaml>=5.1",  # for parsing CLI equal-delimited options\n    # c.f. https://github.com/scikit-hep/pyhf/issues/2593 for excluded v1.16.x versions\n    "scipy>=1.5.4,!=1.16.0,!=1.16.1,!=1.16.2",  # requires numpy, which is required by pyhf\n    "rich>=10.0.0",  # for progress bars\n    "numpy",  # compatible versions controlled through scipy\n]\n\n[project.scripts]\npyhf = "pyhf.cli:cli"\n\n[project.urls]\nDocumentation = "https://pyhf.readthedocs.io/"\nHomepage = "https://github.com/scikit-hep/pyhf"\n"Issue Tracker" = "https://github.com/scikit-hep/pyhf/issues"\n"Release Notes" = "https://pyhf.readthedocs.io/en/stable/release-notes.html"\n"Releases" = "https://github.com/scikit-hep/pyhf/releases"\n"Source Code" = "https://github.com/scikit-hep/pyhf"\n\n[project.optional-dependencies]\nshellcomplete = ["click_completion"]\njax = [\n    "jax>=0.4.1",  # c.f. PR #2079\n    "jaxlib>=0.4.1",  # c.f. PR #2079\n]\nxmlio = ["uproot>=4.1.1"]  # c.f. PR #1567\nminuit = ["iminuit>=2.7.0"]  # c.f. PR #1895\ncontrib = [\n    "matplotlib>=3.0.0",\n    "requests>=2.22.0",\n]\nbackends = ["pyhf[jax,minuit]"]\nall = ["pyhf[backends,xmlio,contrib,shellcomplete]"]\n\n# Developer extras\n[dependency-groups]\ntest = [\n    "scikit-hep-testdata>=0.4.11",\n    "pytest>=6.0",\n    "coverage[toml]>=6.0.0",\n    "pytest-mock",\n    "requests-mock>=1.9.0",\n    "pytest-benchmark[histogram]",\n    "pytest-console-scripts>=1.4.0",\n    "pytest-mpl",\n    "ipympl>=0.3.0",\n    "pydocstyle",\n    "papermill>=2.5.0",\n    "scrapbook>=0.5.0",\n    "notebook>=6.5.7",\n    "graphviz",\n    "pytest-socket>=0.2.0",  # c.f. PR #1917\n]\ndocs = [\n    "pyhf[xmlio,contrib]",\n    "sphinx>=9.0.3",  # c.f. https://github.com/scikit-hep/pyhf/pull/2642\n    "sphinxcontrib-bibtex>=2.1",\n    "sphinx-click>=2.5.0",\n    "pydata-sphinx-theme>=0.15.3",\n    "nbsphinx!=0.8.8",  # c.f. https://github.com/spatialaudio/nbsphinx/issues/620\n    "ipywidgets",\n    "intersphinx_registry>=0.2411.17",\n    "sphinx-issues",\n    "sphinx-copybutton>=0.3.2,!=0.5.1",\n    "jupyterlite-sphinx>=0.13.1",  # c.f. https://github.com/scikit-hep/pyhf/pull/2458\n    "jupyterlite-pyodide-kernel>=0.0.7",\n    "jupytext>=1.14.0",\n    "ipython!=8.7.0",  # c.f. https://github.com/scikit-hep/pyhf/pull/2068\n]\ndev = [\n    "pyhf[all]",\n    "tbump>=6.7.0",\n    "pre-commit",\n    "nox",\n    { include-group = "test" },\n    { include-group = "docs" },\n]\n\n[tool.hatch.version]\nsource = "vcs"\n\n[tool.hatch.version.raw-options]\nlocal_scheme = "no-local-version"\n\n[tool.hatch.build.hooks.vcs]\nversion-file = "src/pyhf/_version.py"\n\n[tool.hatch.build.targets.sdist]\n# only-include needed to properly include src/pyhf/schemas\n# c.f. https://github.com/pypa/hatch/pull/299\n# hatchling always includes:\n# pyproject.toml, .gitignore, any README, any LICENSE, AUTHORS\nonly-include = [\n    "/src",\n    "/CITATION.cff"\n]\nexclude = [\n    "/src/conftest.py"\n]\n\n[tool.hatch.build.targets.wheel]\npackages = ["src/pyhf"]\n\n[tool.black]\nline-length = 88\nskip-string-normalization = true\ninclude = \'\\.pyi?$\'\nexclude = \'\'\'\n/(\n    \\.git\n  | .eggs\n  | build\n  | .nox\n)/\n\'\'\'\n\n[tool.pytest.ini_options]\nminversion = "6.0"\nxfail_strict = true\naddopts = [\n    "-ra",\n    "--showlocals",\n    "--strict-markers",\n    "--strict-config",\n    "--doctest-modules",\n    "--doctest-glob=\'*.rst\'",\n]\nlog_level = "INFO"\ntestpaths = "tests"\nmarkers = [\n    "fail_jax",\n    "fail_numpy",\n    "fail_numpy_minuit",\n    "only_jax",\n    "only_numpy",\n    "only_numpy_minuit",\n    "skip_jax",\n    "skip_numpy",\n    "skip_numpy_minuit",\n]\nfilterwarnings = [\n    "error",\n    \'ignore:the `interpolation=` argument to percentile was renamed to `method=`, which has additional options:DeprecationWarning\',  # Issue #1772\n    "ignore:The interpolation= argument to \'quantile\' is deprecated. Use \'method=\' instead:DeprecationWarning",  # Issue #1772\n    \'ignore: Exception ignored in:pytest.PytestUnraisableExceptionWarning\',  #FIXME: Exception ignored in: <_io.FileIO [closed]>\n    \'ignore:invalid value encountered in (true_)?divide:RuntimeWarning\',  #FIXME\n    \'ignore:invalid value encountered in add:RuntimeWarning\',  #FIXME\n    \'ignore:divide by zero encountered in (true_)?divide:RuntimeWarning\',  #FIXME: pytest tests/test_tensor.py::test_pdf_calculations[numpy]\n    \'ignore:[A-Z]+ is deprecated and will be removed in Pillow 10:DeprecationWarning\',  # keras\n    "ignore:ml_dtypes.float8_e4m3b11 is deprecated.",  #FIXME: Can remove when jaxlib>=0.4.12\n    "ignore:jsonschema.RefResolver is deprecated as of v4.18.0, in favor of the:DeprecationWarning",  # Issue #2139\n    "ignore:Skipping device Apple Paravirtual device that does not support Metal 2.0:UserWarning",  # Can\'t fix given hardware/virtualized device\n    "ignore:jax.xla_computation is deprecated. Please use the AOT APIs:DeprecationWarning",  # jax v0.4.30\n    "ignore:\'MultiCommand\' is deprecated and will be removed in Click 9.0. Use \'Group\' instead.:DeprecationWarning",  # Click\n    "ignore:Jupyter is migrating its paths to use standard platformdirs:DeprecationWarning",  # papermill\n    "ignore:datetime.datetime.utcnow\\\\(\\\\) is deprecated:DeprecationWarning",  # papermill\n]\n\n[tool.coverage.run]\nsource = ["pyhf"]\nbranch = true\nomit = ["*/pyhf/typing.py"]\n\n[tool.coverage.report]\nprecision = 1\nsort = "cover"\nshow_missing = true\nexclude_also = [\n    "if TYPE_CHECKING:"\n]\n\n[tool.mypy]\nfiles = "src"\npython_version = "3.13"\nwarn_unused_configs = true\nstrict = true\nenable_error_code = ["ignore-without-code", "redundant-expr", "truthy-bool"]\nwarn_unreachable = true\nplugins = "numpy.typing.mypy_plugin"\n\n[[tool.mypy.overrides]]\nmodule = [\n  \'jax.*\',\n  \'matplotlib.*\',\n  \'scipy.*\',\n  \'uproot.*\',\n]\nignore_missing_imports = true\n\n[[tool.mypy.overrides]]\nmodule = [\n  \'pyhf\',\n  \'pyhf.optimize.*\',\n  \'pyhf.contrib.*\',\n  \'pyhf.infer.*\',\n  \'pyhf.interpolators.*\',\n  \'pyhf.cli.*\',\n  \'pyhf.modifiers.*\',\n  \'pyhf.exceptions.*\',\n  \'pyhf.parameters.*\',\n  \'pyhf.schema.*\',\n  \'pyhf.writexml\',\n  \'pyhf.workspace\',\n  \'pyhf.patchset\',\n  \'pyhf.compat\',\n  \'pyhf.events\',\n  \'pyhf.utils\',\n  \'pyhf.constraints\',\n  \'pyhf.pdf\',\n  \'pyhf.simplemodels\',\n  \'pyhf.probability\',\n  \'pyhf.tensor.common.*\',\n  \'pyhf.tensor\',\n  \'pyhf.tensor.jax_backend.*\',\n]\nignore_errors = true\n\n[tool.ruff]\nline-length = 88\n\n[tool.ruff.lint]\nextend-select = [\n  "UP",          # pyupgrade\n  "RUF",         # Ruff-specific\n  "TID",         # flake8-tidy-imports\n]\nignore = [\n  "E402",\n  "RUF001", # String contains ambiguous unicode character\n  "RUF005", # unpack-instead-of-concatenating-to-collection-literal\n]\ntyping-modules = ["pyhf.typing"]\nflake8-tidy-imports.ban-relative-imports = "all"\n\n[tool.ruff.lint.per-file-ignores]\n"docs/lite/jupyterlite.py" = ["F401", "F704"]\n"**.ipynb" = ["F821", "F401", "F841", "F811", "E703"]\n',
            'src/pyhf/cli/complete.py': '\'\'\'Shell completions for pyhf.\'\'\'\n\nimport click\n\ntry:\n    import click_completion\n\n    click_completion.init()\n\n    @click.command(help=\'Generate shell completion code.\', name=\'completions\')\n    @click.argument(\n        \'shell\',\n        required=False,\n        type=click_completion.DocumentedChoice(click_completion.core.shells),\n    )\n    def cli(shell):\n        \'\'\'Generate shell completion code for various shells.\'\'\'\n        click.echo(click_completion.core.get_code(shell, prog_name=\'pyhf\'))\n\nexcept ImportError:\n\n    @click.command(help=\'Generate shell completion code.\', name=\'completions\')\n    @click.argument(\'shell\', default=None)\n    def cli(shell):\n        """Placeholder for shell completion code generatioon function if necessary dependency is missing."""\n        click.secho(\n            "This requires the click_completion module.\\n"\n            "You can install it with the shellcomplete extra:\\n"\n            "python -m pip install \'pyhf[shellcomplete]\'"\n        )\n',
            'tests/test_cli.py': "from click.testing import CliRunner\nimport sys\nimport importlib\n\n\ndef test_shllcomplete_cli(isolate_modules):\n    from pyhf.cli.complete import cli\n\n    runner = CliRunner()\n    result = runner.invoke(cli, ['bash'])\n    assert 'complete -F _pyhf_completion -o default pyhf' in result.output\n\n\ndef test_shllcomplete_cli_missing_extra(isolate_modules):\n    sys.modules['click_completion'] = None\n    importlib.reload(sys.modules['pyhf.cli.complete'])\n    from pyhf.cli.complete import cli\n\n    runner = CliRunner()\n    result = runner.invoke(cli, ['bash'])\n    assert 'You can install it with the shellcomplete extra' in result.output\n",
        }
