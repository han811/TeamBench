"""
Parameterized generator for GH23_poetry_10721.

Source PR:    https://github.com/python-poetry/poetry/pull/10721
Source Issue: https://github.com/python-poetry/poetry/issues/10422

Seed varies: renames 'accepted' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH23_poetry_10721'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH23_poetry_10721'
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
                files[fpath] = files[fpath].replace('accepted', 'accepted' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH23_poetry_10721',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'python-poetry/poetry',
                "pr_number": 10721,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/python-poetry/poetry/pull/10721",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'src/poetry/console/commands/update.py': 'from __future__ import annotations\n\nfrom typing import TYPE_CHECKING\nfrom typing import ClassVar\n\nfrom cleo.helpers import argument\nfrom cleo.helpers import option\n\nfrom poetry.console.commands.installer_command import InstallerCommand\n\n\nif TYPE_CHECKING:\n    from cleo.io.inputs.argument import Argument\n    from cleo.io.inputs.option import Option\n\n\nclass UpdateCommand(InstallerCommand):\n    name = "update"\n    description = (\n        "Update the dependencies as according to the <comment>pyproject.toml</> file."\n    )\n\n    arguments: ClassVar[list[Argument]] = [\n        argument("packages", "The packages to update", optional=True, multiple=True)\n    ]\n    options: ClassVar[list[Option]] = [\n        *InstallerCommand._group_dependency_options(),\n        option(\n            "sync",\n            None,\n            "Synchronize the environment with the locked packages and the specified"\n            " groups.",\n        ),\n        option(\n            "dry-run",\n            None,\n            "Output the operations but do not execute anything "\n            "(implicitly enables --verbose).",\n        ),\n        option("lock", None, "Do not perform operations (only update the lockfile)."),\n    ]\n\n    loggers: ClassVar[list[str]] = ["poetry.repositories.pypi_repository"]\n\n    def handle(self) -> int:\n        packages = self.argument("packages")\n        if packages:\n            self.installer.whitelist(dict.fromkeys(packages, "*"))\n\n        self.installer.only_groups(self.activated_groups)\n        self.installer.dry_run(self.option("dry-run"))\n        self.installer.requires_synchronization(self.option("sync"))\n        self.installer.execute_operations(not self.option("lock"))\n\n        # Force update\n        self.installer.update(True)\n\n        return self.installer.run()\n',
            'tests/console/commands/test_update.py': 'from __future__ import annotations\n\nfrom typing import TYPE_CHECKING\n\nimport pytest\n\nfrom poetry.console.commands.update import UpdateCommand\nfrom tests.helpers import get_package\n\n\nif TYPE_CHECKING:\n    from pytest_mock import MockerFixture\n\n    from poetry.poetry import Poetry\n    from tests.helpers import TestRepository\n    from tests.types import CommandTesterFactory\n    from tests.types import FixtureDirGetter\n    from tests.types import ProjectFactory\n\n\n@pytest.fixture\ndef poetry_with_outdated_lockfile(\n    project_factory: ProjectFactory, fixture_dir: FixtureDirGetter\n) -> Poetry:\n    source = fixture_dir("outdated_lock")\n\n    return project_factory(\n        name="foobar",\n        pyproject_content=(source / "pyproject.toml").read_text(encoding="utf-8"),\n        poetry_lock_content=(source / "poetry.lock").read_text(encoding="utf-8"),\n    )\n\n\n@pytest.mark.parametrize(\n    "command",\n    [\n        "--dry-run",\n        "docker --dry-run",\n    ],\n)\ndef test_update_with_dry_run_keep_files_intact(\n    command: str,\n    poetry_with_outdated_lockfile: Poetry,\n    repo: TestRepository,\n    command_tester_factory: CommandTesterFactory,\n) -> None:\n    tester = command_tester_factory("update", poetry=poetry_with_outdated_lockfile)\n\n    original_pyproject_content = poetry_with_outdated_lockfile.file.read()\n    original_lockfile_content = poetry_with_outdated_lockfile._locker.lock_data\n\n    repo.add_package(get_package("docker", "4.3.0"))\n    repo.add_package(get_package("docker", "4.3.1"))\n\n    tester.execute(command)\n\n    assert poetry_with_outdated_lockfile.file.read() == original_pyproject_content\n    assert poetry_with_outdated_lockfile._locker.lock_data == original_lockfile_content\n\n\n@pytest.mark.parametrize(\n    ("command", "expected"),\n    [\n        ("", True),\n        ("--dry-run", True),\n        ("--lock", False),\n    ],\n)\ndef test_update_prints_operations(\n    command: str,\n    expected: bool,\n    poetry_with_outdated_lockfile: Poetry,\n    repo: TestRepository,\n    command_tester_factory: CommandTesterFactory,\n) -> None:\n    tester = command_tester_factory("update", poetry=poetry_with_outdated_lockfile)\n\n    repo.add_package(get_package("docker", "4.3.0"))\n    repo.add_package(get_package("docker", "4.3.1"))\n\n    tester.execute(command)\n    output = tester.io.fetch_output()\n\n    assert ("Package operations:" in output) is expected\n    assert ("Installing docker (4.3.1)" in output) is expected\n\n\ndef test_update_sync_option_is_passed_to_the_installer(\n    poetry_with_outdated_lockfile: Poetry,\n    command_tester_factory: CommandTesterFactory,\n    mocker: MockerFixture,\n) -> None:\n    """\n    The --sync option is passed properly to the installer from update.\n    """\n    tester = command_tester_factory("update", poetry=poetry_with_outdated_lockfile)\n    assert isinstance(tester.command, UpdateCommand)\n    mocker.patch.object(tester.command.installer, "run", return_value=1)\n\n    tester.execute("--sync")\n\n    assert tester.command.installer._requires_synchronization\n',
        }
