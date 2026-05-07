"""
Parameterized generator for GH582_boto3_4685.

Source PR:    https://github.com/boto/boto3/pull/4685
Source Issue: N/A

Seed varies: renames 'botocore' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH582_boto3_4685'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH582_boto3_4685'
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
                files[fpath] = files[fpath].replace('botocore', 'botocore' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH582_boto3_4685',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'boto/boto3',
                "pr_number": 4685,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/boto/boto3/pull/4685",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'tests/__init__.py': '# Copyright 2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.\n#\n# Licensed under the Apache License, Version 2.0 (the "License"). You\n# may not use this file except in compliance with the License. A copy of\n# the License is located at\n#\n# https://aws.amazon.com/apache2.0/\n#\n# or in the "license" file accompanying this file. This file is\n# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF\n# ANY KIND, either express or implied. See the License for the specific\n# language governing permissions and limitations under the License.\n\nimport random\nimport time\nimport unittest\nfrom unittest import mock\n\nfrom botocore.compat import HAS_CRT\n\n\ndef unique_id(name):\n    """\n    Generate a unique ID that includes the given name,\n    a timestamp and a random number. This helps when running\n    integration tests in parallel that must create remote\n    resources.\n    """\n    return f\'{name}-{int(time.time())}-{random.randint(0, 10000)}\'\n\n\nclass BaseTestCase(unittest.TestCase):\n    """\n    A base test case which mocks out the low-level session to prevent\n    any actual calls to Botocore.\n    """\n\n    def setUp(self):\n        self.bc_session_patch = mock.patch(\'botocore.session.Session\')\n        self.bc_session_cls = self.bc_session_patch.start()\n\n        loader = self.bc_session_cls.return_value.get_component.return_value\n        loader.data_path = \'\'\n        self.loader = loader\n\n        # We also need to patch the global default session.\n        # Otherwise it could be a cached real session came from previous\n        # "functional" or "integration" tests.\n        patch_global_session = mock.patch(\'boto3.DEFAULT_SESSION\')\n        patch_global_session.start()\n        self.addCleanup(patch_global_session.stop)\n\n    def tearDown(self):\n        self.bc_session_patch.stop()\n\n\ndef requires_crt(reason=None):\n    if reason is None:\n        reason = "Test requires awscrt to be installed"\n\n    def decorator(func):\n        return unittest.skipIf(not HAS_CRT, reason)(func)\n\n    return decorator\n',
        }
