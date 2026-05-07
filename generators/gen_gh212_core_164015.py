"""
Parameterized generator for GH212_core_164015.

Source PR:    https://github.com/home-assistant/core/pull/164015
Source Issue: N/A

Seed varies: renames 'ascii' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH212_core_164015'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH212_core_164015'
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
                files[fpath] = files[fpath].replace('ascii', 'ascii' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH212_core_164015',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'home-assistant/core',
                "pr_number": 164015,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/home-assistant/core/pull/164015",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'homeassistant/util/file.py': '"""File utility functions."""\n\nfrom __future__ import annotations\n\nimport logging\nimport os\nimport tempfile\n\nfrom atomicwrites import AtomicWriter\n\nfrom homeassistant.exceptions import HomeAssistantError\n\n_LOGGER = logging.getLogger(__name__)\n\n\nclass WriteError(HomeAssistantError):\n    """Error writing the data."""\n\n\ndef write_utf8_file_atomic(\n    filename: str, utf8_data: bytes | str, private: bool = False, mode: str = "w"\n) -> None:\n    """Write a file and rename it into place using atomicwrites.\n\n    Writes all or nothing.\n\n    This function uses fsync under the hood. It should\n    only be used to write mission critical files as\n    fsync can block for a few seconds or longer is the\n    disk is busy.\n\n    Using this function frequently will significantly\n    negatively impact performance.\n    """\n    try:\n        with AtomicWriter(filename, mode=mode, overwrite=True).open() as fdesc:\n            if not private:\n                os.fchmod(fdesc.fileno(), 0o644)\n            fdesc.write(utf8_data)\n    except OSError as error:\n        _LOGGER.exception("Saving file failed: %s", filename)\n        raise WriteError(error) from error\n\n\ndef write_utf8_file(\n    filename: str, utf8_data: bytes | str, private: bool = False, mode: str = "w"\n) -> None:\n    """Write a file and rename it into place.\n\n    Writes all or nothing.\n    """\n    tmp_filename = ""\n    encoding = "utf-8" if "b" not in mode else None\n    try:\n        # Modern versions of Python tempfile create this file with mode 0o600\n        with tempfile.NamedTemporaryFile(\n            mode=mode, encoding=encoding, dir=os.path.dirname(filename), delete=False\n        ) as fdesc:\n            fdesc.write(utf8_data)\n            tmp_filename = fdesc.name\n            if not private:\n                os.fchmod(fdesc.fileno(), 0o644)\n        os.replace(tmp_filename, filename)\n    except OSError as error:\n        _LOGGER.exception("Saving file failed: %s", filename)\n        raise WriteError(error) from error\n    finally:\n        if os.path.exists(tmp_filename):\n            try:\n                os.remove(tmp_filename)\n            except OSError as err:\n                # If we are cleaning up then something else went wrong, so\n                # we should suppress likely follow-on errors in the cleanup\n                _LOGGER.error(\n                    "File replacement cleanup failed for %s while saving %s: %s",\n                    tmp_filename,\n                    filename,\n                    err,\n                )\n',
            'tests/util/test_file.py': '"""Test Home Assistant file utility functions."""\n\nimport os\nfrom pathlib import Path\nfrom unittest.mock import patch\n\nimport py\nimport pytest\n\nfrom homeassistant.util.file import WriteError, write_utf8_file, write_utf8_file_atomic\n\n\n@pytest.mark.parametrize("func", [write_utf8_file, write_utf8_file_atomic])\ndef test_write_utf8_file_atomic_private(tmpdir: py.path.local, func) -> None:\n    """Test files can be written as 0o600 or 0o644."""\n    test_dir = tmpdir.mkdir("files")\n    test_file = Path(test_dir / "test.json")\n\n    func(test_file, \'{"some":"data"}\', False)\n    with open(test_file, encoding="utf8") as fh:\n        assert fh.read() == \'{"some":"data"}\'\n    assert os.stat(test_file).st_mode & 0o777 == 0o644\n\n    func(test_file, \'{"some":"data"}\', True)\n    with open(test_file, encoding="utf8") as fh:\n        assert fh.read() == \'{"some":"data"}\'\n    assert os.stat(test_file).st_mode & 0o777 == 0o600\n\n    func(test_file, b\'{"some":"data"}\', True, mode="wb")\n    with open(test_file, encoding="utf8") as fh:\n        assert fh.read() == \'{"some":"data"}\'\n    assert os.stat(test_file).st_mode & 0o777 == 0o600\n\n\ndef test_write_utf8_file_fails_at_creation(tmpdir: py.path.local) -> None:\n    """Test that failed creation of the temp file does not create an empty file."""\n    test_dir = tmpdir.mkdir("files")\n    test_file = Path(test_dir / "test.json")\n\n    with (\n        pytest.raises(WriteError),\n        patch(\n            "homeassistant.util.file.tempfile.NamedTemporaryFile", side_effect=OSError\n        ),\n    ):\n        write_utf8_file(test_file, \'{"some":"data"}\', False)\n\n    assert not os.path.exists(test_file)\n\n\ndef test_write_utf8_file_fails_at_rename(\n    tmpdir: py.path.local, caplog: pytest.LogCaptureFixture\n) -> None:\n    """Test that if rename fails not not remove, we do not log the failed cleanup."""\n    test_dir = tmpdir.mkdir("files")\n    test_file = Path(test_dir / "test.json")\n\n    with (\n        pytest.raises(WriteError),\n        patch("homeassistant.util.file.os.replace", side_effect=OSError),\n    ):\n        write_utf8_file(test_file, \'{"some":"data"}\', False)\n\n    assert not os.path.exists(test_file)\n\n    assert "File replacement cleanup failed" not in caplog.text\n\n\ndef test_write_utf8_file_fails_at_rename_and_remove(\n    tmpdir: py.path.local, caplog: pytest.LogCaptureFixture\n) -> None:\n    """Test that if rename and remove both fail, we log the failed cleanup."""\n    test_dir = tmpdir.mkdir("files")\n    test_file = Path(test_dir / "test.json")\n\n    with (\n        pytest.raises(WriteError),\n        patch("homeassistant.util.file.os.remove", side_effect=OSError),\n        patch("homeassistant.util.file.os.replace", side_effect=OSError),\n    ):\n        write_utf8_file(test_file, \'{"some":"data"}\', False)\n\n    assert "File replacement cleanup failed" in caplog.text\n\n\ndef test_write_utf8_file_atomic_fails(tmpdir: py.path.local) -> None:\n    """Test OSError from write_utf8_file_atomic is rethrown as WriteError."""\n    test_dir = tmpdir.mkdir("files")\n    test_file = Path(test_dir / "test.json")\n\n    with (\n        pytest.raises(WriteError),\n        patch("homeassistant.util.file.AtomicWriter.open", side_effect=OSError),\n    ):\n        write_utf8_file_atomic(test_file, \'{"some":"data"}\', False)\n\n    assert not os.path.exists(test_file)\n',
        }
