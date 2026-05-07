"""
Parameterized generator for GH31_poetry_10716.

Source PR:    https://github.com/python-poetry/poetry/pull/10716
Source Issue: https://github.com/python-poetry/poetry/issues/10395

Seed varies: renames 'activate' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH31_poetry_10716'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH31_poetry_10716'
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
                files[fpath] = files[fpath].replace('activate', 'activate' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH31_poetry_10716',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'python-poetry/poetry',
                "pr_number": 10716,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/python-poetry/poetry/pull/10716",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'src/poetry/console/commands/env/activate.py': 'from __future__ import annotations\n\nimport shlex\n\nfrom typing import TYPE_CHECKING\n\nimport shellingham\n\nfrom poetry.console.commands.env_command import EnvCommand\nfrom poetry.utils._compat import WINDOWS\n\n\nif TYPE_CHECKING:\n    from poetry.utils.env import Env\n\n\nclass ShellNotSupportedError(Exception):\n    """Raised when a shell doesn\'t have an activator in virtual environment"""\n\n\nclass EnvActivateCommand(EnvCommand):\n    name = "env activate"\n    description = "Print the command to activate a virtual environment."\n\n    def handle(self) -> int:\n        from poetry.utils.env import EnvManager\n\n        env = EnvManager(self.poetry).get()\n\n        try:\n            shell, _ = shellingham.detect_shell()\n        except shellingham.ShellDetectionFailure:\n            shell = ""\n\n        if command := self._get_activate_command(env, shell):\n            self.line(command)\n            return 0\n\n        raise ShellNotSupportedError(\n            f"Discovered shell \'{shell}\' doesn\'t have an activator in virtual environment"\n        )\n\n    def _get_activate_command(self, env: Env, shell: str) -> str:\n        if shell == "fish":\n            command, filename = "source", "activate.fish"\n        elif shell == "nu":\n            command, filename = "overlay use", "activate.nu"\n        elif shell in ["csh", "tcsh"]:\n            command, filename = "source", "activate.csh"\n        elif shell in ["powershell", "pwsh"]:\n            command, filename = ".", "activate.ps1"\n        elif shell == "cmd":\n            command, filename = ".", "activate.bat"\n        elif shell in ["bash", "mksh", "zsh"]:\n            command, filename = "source", "activate"\n        else:\n            command, filename = ".", "activate"\n\n        if (activation_script := env.bin_dir / filename).exists():\n            if WINDOWS:\n                return f"{self._quote(str(activation_script), shell)}"\n            return f"{command} {self._quote(str(activation_script), shell)}"\n        return ""\n\n    @staticmethod\n    def _quote(command: str, shell: str) -> str:\n        if WINDOWS:\n            if shell == "cmd":\n                return f\'"{command}"\'\n            if shell in ["powershell", "pwsh"]:\n                return f\'& "{command}"\'\n        return shlex.quote(command)\n',
            'tests/console/commands/env/test_activate.py': 'from __future__ import annotations\n\nfrom typing import TYPE_CHECKING\n\nimport pytest\n\nfrom poetry.utils._compat import WINDOWS\n\n\nif TYPE_CHECKING:\n    from cleo.testers.application_tester import ApplicationTester\n    from cleo.testers.command_tester import CommandTester\n    from pytest_mock import MockerFixture\n\n    from poetry.utils.env import VirtualEnv\n    from tests.types import CommandTesterFactory\n\n\n@pytest.fixture\ndef tester(command_tester_factory: CommandTesterFactory) -> CommandTester:\n    return command_tester_factory("env activate")\n\n\n@pytest.mark.parametrize(\n    "shell, command, ext",\n    (\n        ("dash", ".", ""),\n        ("bash", "source", ""),\n        ("zsh", "source", ""),\n        ("fish", "source", ".fish"),\n        ("nu", "overlay use", ".nu"),\n        ("csh", "source", ".csh"),\n        ("tcsh", "source", ".csh"),\n    ),\n)\n@pytest.mark.skipif(WINDOWS, reason="Only Unix shells")\ndef test_env_activate_prints_correct_script(\n    tmp_venv: VirtualEnv,\n    mocker: MockerFixture,\n    tester: CommandTester,\n    shell: str,\n    command: str,\n    ext: str,\n) -> None:\n    mocker.patch("shellingham.detect_shell", return_value=(shell, None))\n    mocker.patch("poetry.utils.env.EnvManager.get", return_value=tmp_venv)\n\n    tester.execute()\n\n    line = tester.io.fetch_output().rstrip("\\n")\n    assert line == f"{command} {tmp_venv.bin_dir}/activate{ext}"\n\n\n@pytest.mark.parametrize(\n    "shell, command, ext, prefix",\n    (\n        ("cmd", ".", "activate.bat", ""),\n        ("pwsh", ".", "activate.ps1", "& "),\n        ("powershell", ".", "activate.ps1", "& "),\n    ),\n)\n@pytest.mark.skipif(not WINDOWS, reason="Only Windows shells")\ndef test_env_activate_prints_correct_script_on_windows(\n    tmp_venv: VirtualEnv,\n    mocker: MockerFixture,\n    tester: CommandTester,\n    shell: str,\n    command: str,\n    ext: str,\n    prefix: str,\n) -> None:\n    mocker.patch("shellingham.detect_shell", return_value=(shell, None))\n    mocker.patch("poetry.utils.env.EnvManager.get", return_value=tmp_venv)\n\n    tester.execute()\n\n    line = tester.io.fetch_output().rstrip("\\n")\n    assert line == f\'{prefix}"{tmp_venv.bin_dir / ext!s}"\'\n\n\n@pytest.mark.parametrize("verbosity", ["", "-v", "-vv", "-vvv"])\ndef test_no_additional_output_in_verbose_mode(\n    tmp_venv: VirtualEnv,\n    mocker: MockerFixture,\n    app_tester: ApplicationTester,\n    verbosity: str,\n) -> None:\n    mocker.patch("shellingham.detect_shell", return_value=("pwsh", None))\n    mocker.patch("poetry.utils.env.EnvManager.get", return_value=tmp_venv)\n\n    # use an AppTester instead of a CommandTester to catch additional output\n    app_tester.execute(f"env activate {verbosity}")\n\n    lines = app_tester.io.fetch_output().splitlines()\n    assert len(lines) == 1\n',
        }
