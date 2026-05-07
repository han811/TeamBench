"""
Parameterized generator for GH1202_wandb_11491.

Source PR:    https://github.com/wandb/wandb/pull/11491
Source Issue: N/A

Seed varies: renames 'affected' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH1202_wandb_11491'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH1202_wandb_11491'
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
                files[fpath] = files[fpath].replace('affected', 'affected' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH1202_wandb_11491',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'wandb/wandb',
                "pr_number": 11491,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/wandb/wandb/pull/11491",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'CHANGELOG.unreleased.md': '# Unreleased changes\n\nAdd here any changes made in a PR that are relevant to end users. Allowed\nsections:\n\n- Added - for new features.\n- Changed - for changes in existing functionality.\n- Deprecated - for soon-to-be removed features.\n- Removed - for now removed features.\n- Fixed - for any bug fixes.\n- Security - in case of vulnerabilities.\n\nSection headings should be at level 3 (e.g. `### Added`).\n\n## Unreleased\n\n### Added\n\n- `wandb beta core start|stop` commands to run a detached `wandb-core` service and reuse it across multiple processes via the `WANDB_SERVICE` env var (@dmitryduev in https://github.com/wandb/wandb/pull/11418)\n\n### Changed\n\n- JSON serialization and deserialization now use `orjson` for improved performance (@jacobromero in https://github.com/wandb/wandb/pull/11163)\n',
            'tests/unit_tests/test_lib/test_runid.py': 'import random\n\nimport pytest\nfrom wandb.sdk.lib import runid\n\n\ndef test_generate_id_is_base36():\n    # Given reasonable randomness assumptions, generating an 1000-digit string should\n    # hit all 36 characters at least once >99.9999999999% of the time.\n    new_id = runid.generate_id(1000)\n    assert len(new_id) == 1000\n    assert set(new_id) == set("0123456789abcdefghijklmnopqrstuvwxyz")\n\n\ndef test_generate_id_default_8_chars():\n    assert len(runid.generate_id()) == 8\n\n\n@pytest.fixture\ndef isolate_random_state():\n    orig_state = random.getstate()\n    try:\n        yield\n    finally:\n        random.setstate(orig_state)\n\n\n@pytest.mark.usefixtures("isolate_random_state")\ndef test_generate_fast_id_independent_of_global_seed():\n    random.seed(42)\n    id1 = runid.generate_fast_id(128)\n\n    random.seed(42)\n    id2 = runid.generate_fast_id(128)\n\n    assert id1 != id2, "generate_fast_id should not be affected by global random.seed()"\n',
            'wandb/sdk/lib/runid.py': '"""runid util."""\n\nimport random\nimport secrets\nfrom string import ascii_lowercase, digits\n\n_ID_CHARS = f"{ascii_lowercase}{digits}"\n\n# Create a dedicated Random instance with its own state so it\n# is not affected by global random.seed() calls\n_random = random.Random()\n\n\ndef generate_id(length: int = 8) -> str:\n    """Generate a random base-36 string of `length` digits."""\n    # There are ~2.8T base-36 8-digit strings. If we generate 210k ids,\n    # we\'ll have a ~1% chance of collision.\n    return "".join(secrets.choice(_ID_CHARS) for _ in range(length))\n\n\ndef generate_fast_id(length: int = 8) -> str:\n    """Faster alternative to `generate_id` if cryptographic strength isn\'t needed.\n\n    In local testing at the time of implementation, this is ~30-50x faster than\n    `generate_id` when generating 128-character IDs.\n\n    Uses a dedicated Random instance to avoid being affected by global\n    random.seed() calls from user code or libraries.\n    """\n    return "".join(_random.choices(_ID_CHARS, k=length))\n',
        }
