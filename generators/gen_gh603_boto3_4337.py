"""
Parameterized generator for GH603_boto3_4337.

Source PR:    https://github.com/boto/boto3/pull/4337
Source Issue: N/A

Seed varies: renames 'account' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH603_boto3_4337'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH603_boto3_4337'
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
                files[fpath] = files[fpath].replace('account', 'account' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH603_boto3_4337',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'boto/boto3',
                "pr_number": 4337,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/boto/boto3/pull/4337",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'docs/source/guide/s3-example-creating-buckets.rst': '.. Copyright 2010-2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.\n\n   This work is licensed under a Creative Commons Attribution-NonCommercial-ShareAlike 4.0\n   International License (the "License"). You may not use this file except in compliance with the\n   License. A copy of the License is located at http://creativecommons.org/licenses/by-nc-sa/4.0/.\n\n   This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,\n   either express or implied. See the License for the specific language governing permissions and\n   limitations under the License.\n\n\n#################\nAmazon S3 buckets\n#################\n\nAn Amazon S3 bucket is a storage location to hold files. S3 files are referred \nto as objects.\n\nThis section describes how to use the AWS SDK for Python to perform common \noperations on S3 buckets.\n\n\nCreate an Amazon S3 bucket\n==========================\n\nThe name of an Amazon S3 bucket must be unique across all regions of the AWS \nplatform. The bucket can be located in a specific region to minimize latency\nor to address regulatory requirements.\n\n.. code-block:: python\n\n    import logging\n    import boto3\n    from botocore.exceptions import ClientError\n\n\n    def create_bucket(bucket_name, region=None):\n        """Create an S3 bucket in a specified region\n\n        If a region is not specified, the bucket is created in the S3 default\n        region (us-east-1).\n\n        :param bucket_name: Bucket to create\n        :param region: String region to create bucket in, e.g., \'us-west-2\'\n        :return: True if bucket created, else False\n        """\n\n        # Create bucket\n        try:\n            if region is None:\n                s3_client = boto3.client(\'s3\')\n                s3_client.create_bucket(Bucket=bucket_name)\n            else:\n                s3_client = boto3.client(\'s3\', region_name=region)\n                location = {\'LocationConstraint\': region}\n                s3_client.create_bucket(Bucket=bucket_name,\n                                        CreateBucketConfiguration=location)\n        except ClientError as e:\n            logging.error(e)\n            return False\n        return True\n\n\nList existing buckets\n=====================\n\nList all the existing buckets for the AWS account.\n\n.. code-block:: python\n\n    # Retrieve the list of existing buckets\n    s3 = boto3.client(\'s3\')\n    response = s3.list_buckets()\n\n    # Output the bucket names\n    print(\'Existing buckets:\')\n    for bucket in response[\'Buckets\']:\n        print(f\'  {bucket["Name"]}\')\n\n',
        }
