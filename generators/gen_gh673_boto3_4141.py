"""
Parameterized generator for GH673_boto3_4141.

Source PR:    https://github.com/boto/boto3/pull/4141
Source Issue: https://github.com/boto/boto3/issues/4117

Seed varies: renames 'active' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH673_boto3_4141'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH673_boto3_4141'
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
                files[fpath] = files[fpath].replace('active', 'active' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH673_boto3_4141',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'boto/boto3',
                "pr_number": 4141,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/boto/boto3/pull/4141",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'docs/source/reference/customizations/dynamodb.rst': '.. _ref_custom_dynamodb:\n\n================================\nDynamoDB customization reference\n================================\n\n.. _ref_valid_dynamodb_types:\n\nValid DynamoDB types\n--------------------\n\nThese are the valid item types to use with Boto3 Table Resource (:py:class:`dynamodb.Table`) and DynamoDB:\n\n+----------------------------------------------+-----------------------------+\n| Python Type                                  | DynamoDB Type               |\n+==============================================+=============================+\n| string                                       | String (S)                  |\n+----------------------------------------------+-----------------------------+\n| integer                                      | Number (N)                  |\n+----------------------------------------------+-----------------------------+\n| :py:class:`decimal.Decimal`                  | Number (N)                  |\n+----------------------------------------------+-----------------------------+\n| :py:class:`boto3.dynamodb.types.Binary`      | Binary (B)                  |\n+----------------------------------------------+-----------------------------+\n| boolean                                      | Boolean (BOOL)              |\n+----------------------------------------------+-----------------------------+\n| ``None``                                     | Null (NULL)                 |\n+----------------------------------------------+-----------------------------+\n| string set                                   | String Set (SS)             |\n+----------------------------------------------+-----------------------------+\n| integer set                                  | Number Set (NS)             |\n+----------------------------------------------+-----------------------------+\n| :py:class:`decimal.Decimal` set              | Number Set (NS)             |\n+----------------------------------------------+-----------------------------+\n| :py:class:`boto3.dynamodb.types.Binary` set  | Binary Set (BS)             |\n+----------------------------------------------+-----------------------------+\n| list                                         | List (L)                    |\n+----------------------------------------------+-----------------------------+\n| dict                                         | Map (M)                     |\n+----------------------------------------------+-----------------------------+\n\n\nCustom Boto3 types\n------------------\n\n\n.. autoclass:: boto3.dynamodb.types.Binary\n   :members:\n   :undoc-members:\n\n.. _ref_dynamodb_conditions:\n\nDynamoDB conditions\n-------------------\n\n.. autoclass:: boto3.dynamodb.conditions.Key\n   :members:\n   :undoc-members:\n   :inherited-members:\n\n.. autoclass:: boto3.dynamodb.conditions.Attr\n   :members:\n   :undoc-members:\n   :inherited-members:\n',
        }
