"""
Parameterized generator for GH492_boto3_4734.

Source PR:    https://github.com/boto/boto3/pull/4734
Source Issue: N/A

Seed varies: renames 'awscrt' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH492_boto3_4734'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH492_boto3_4734'
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
                files[fpath] = files[fpath].replace('awscrt', 'awscrt' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH492_boto3_4734',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'boto/boto3',
                "pr_number": 4734,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/boto/boto3/pull/4734",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'tests/__init__.py': '# Copyright 2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.\n#\n# Licensed under the Apache License, Version 2.0 (the "License"). You\n# may not use this file except in compliance with the License. A copy of\n# the License is located at\n#\n# https://aws.amazon.com/apache2.0/\n#\n# or in the "license" file accompanying this file. This file is\n# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF\n# ANY KIND, either express or implied. See the License for the specific\n# language governing permissions and limitations under the License.\n\nimport unittest\nimport uuid\nfrom unittest import mock\n\nfrom botocore.compat import HAS_CRT\n\n\ndef unique_id(name):\n    """\n    Generate a unique ID for integration tests\n    that create remote resources in parallel.\n    """\n    return f"{name}-{uuid.uuid4().hex}"\n\n\nclass BaseTestCase(unittest.TestCase):\n    """\n    A base test case which mocks out the low-level session to prevent\n    any actual calls to Botocore.\n    """\n\n    def setUp(self):\n        self.bc_session_patch = mock.patch(\'botocore.session.Session\')\n        self.bc_session_cls = self.bc_session_patch.start()\n\n        loader = self.bc_session_cls.return_value.get_component.return_value\n        loader.data_path = \'\'\n        self.loader = loader\n\n        # We also need to patch the global default session.\n        # Otherwise it could be a cached real session came from previous\n        # "functional" or "integration" tests.\n        patch_global_session = mock.patch(\'boto3.DEFAULT_SESSION\')\n        patch_global_session.start()\n        self.addCleanup(patch_global_session.stop)\n\n    def tearDown(self):\n        self.bc_session_patch.stop()\n\n\ndef requires_crt(reason=None):\n    if reason is None:\n        reason = "Test requires awscrt to be installed"\n\n    def decorator(func):\n        return unittest.skipIf(not HAS_CRT, reason)(func)\n\n    return decorator\n',
            'tests/unit/test_crt.py': '# Copyright 2023 Amazon.com, Inc. or its affiliates. All Rights Reserved.\n#\n# Licensed under the Apache License, Version 2.0 (the "License"). You\n# may not use this file except in compliance with the License. A copy of\n# the License is located at\n#\n# https://aws.amazon.com/apache2.0/\n#\n# or in the "license" file accompanying this file. This file is\n# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF\n# ANY KIND, either express or implied. See the License for the specific\n# language governing permissions and limitations under the License.\nimport botocore.exceptions\nimport pytest\nimport s3transfer\nfrom botocore.compat import HAS_CRT\nfrom botocore.credentials import Credentials\n\nimport boto3\nfrom boto3.s3.transfer import TransferConfig\nfrom tests import mock, requires_crt\n\nif HAS_CRT:\n    from awscrt.s3 import CrossProcessLock as CrossProcessLockClass\n    from s3transfer.crt import BotocoreCRTCredentialsWrapper\n\n    import boto3.crt\n\n\n@pytest.fixture\ndef mock_crt_process_lock(monkeypatch):\n    # The process lock is cached at the module layer whenever the\n    # cross process lock is successfully acquired. This patch ensures that\n    # test cases will start off with no previously cached process lock and\n    # if a cross process is instantiated/acquired it will be the mock that\n    # can be used for controlling lock behavior.\n    if HAS_CRT:\n        monkeypatch.setattr(\'s3transfer.crt.CRT_S3_PROCESS_LOCK\', None)\n        with mock.patch(\'awscrt.s3.CrossProcessLock\', spec=True) as mock_lock:\n            yield mock_lock\n    else:\n        # We cannot mock or use the lock without CRT support.\n        yield None\n\n\n@pytest.fixture\ndef mock_crt_client_singleton(monkeypatch):\n    # Clear CRT state for each test\n    if HAS_CRT:\n        monkeypatch.setattr(\'boto3.crt.CRT_S3_CLIENT\', None)\n    yield None\n\n\n@pytest.fixture\ndef mock_serializer_singleton(monkeypatch):\n    # Clear CRT state for each test\n    if HAS_CRT:\n        monkeypatch.setattr(\'boto3.crt.BOTOCORE_CRT_SERIALIZER\', None)\n    yield None\n\n\ndef create_test_client(service_name=\'s3\', region_name="us-east-1"):\n    return boto3.client(\n        service_name,\n        region_name=region_name,\n        aws_access_key_id="access",\n        aws_secret_access_key="secret",\n        aws_session_token="token",\n    )\n\n\nUSW2_S3_CLIENT = create_test_client(region_name="us-west-2")\nUSE1_S3_CLIENT = create_test_client(region_name="us-east-1")\n\n\nclass TestCRTTransferManager:\n    @requires_crt()\n    def test_create_crt_transfer_manager_with_lock_in_use(\n        self,\n        mock_crt_process_lock,\n        mock_crt_client_singleton,\n        mock_serializer_singleton,\n    ):\n        mock_crt_process_lock.return_value.acquire.side_effect = RuntimeError\n\n        # Verify we can\'t create a second CRT client\n        tm = boto3.crt.create_crt_transfer_manager(USW2_S3_CLIENT, None)\n        assert tm is None\n\n    @requires_crt()\n    def test_create_crt_transfer_manager(\n        self,\n        mock_crt_process_lock,\n        mock_crt_client_singleton,\n        mock_serializer_singleton,\n    ):\n        tm = boto3.crt.create_crt_transfer_manager(USW2_S3_CLIENT, None)\n        assert isinstance(tm, s3transfer.crt.CRTTransferManager)\n\n    @requires_crt()\n    def test_crt_singleton_is_returned_every_call(\n        self,\n        mock_crt_process_lock,\n        mock_crt_client_singleton,\n        mock_serializer_singleton,\n    ):\n        first_s3_client = boto3.crt.get_crt_s3_client(USW2_S3_CLIENT, None)\n        second_s3_client = boto3.crt.get_crt_s3_client(USW2_S3_CLIENT, None)\n\n        assert isinstance(first_s3_client, boto3.crt.CRTS3Client)\n        assert first_s3_client is second_s3_client\n        assert first_s3_client.crt_client is second_s3_client.crt_client\n\n    @requires_crt()\n    def test_create_crt_transfer_manager_w_client_in_wrong_region(\n        self,\n        mock_crt_process_lock,\n        mock_crt_client_singleton,\n        mock_serializer_singleton,\n    ):\n        """Ensure we don\'t return the crt transfer manager if client is in\n        different region. The CRT isn\'t able to handle region redirects and\n        will consistently fail.\n\n        We can remove this test once we have this fixed on the CRT side.\n        """\n        usw2_s3_client = boto3.crt.create_crt_transfer_manager(\n            USW2_S3_CLIENT, None\n        )\n        assert isinstance(usw2_s3_client, boto3.crt.CRTTransferManager)\n\n        use1_s3_client = boto3.crt.create_crt_transfer_manager(\n            USE1_S3_CLIENT, None\n        )\n        assert use1_s3_client is None\n\n    @pytest.mark.parametrize(\n        "boto3_tuple,crt_tuple,matching",\n        (\n            (\n                ("access", "secret", "token"),\n                ("access", "secret", "token"),\n                True,\n            ),\n            (\n                ("access", "secret", "token"),\n                ("noaccess", "secret", "token"),\n                False,\n            ),\n            (\n                ("access", "secret", "token"),\n                ("access", "nosecret", "token"),\n                False,\n            ),\n            (\n                ("access", "secret", "token"),\n                ("access", "secret", "notoken"),\n                False,\n            ),\n        ),\n    )\n    @requires_crt()\n    def test_compare_identities(self, boto3_tuple, crt_tuple, matching):\n        boto3_creds = Credentials(*boto3_tuple)\n        crt_creds = Credentials(*crt_tuple)\n        crt_creds_wrapper = BotocoreCRTCredentialsWrapper(crt_creds)\n        assert (\n            boto3.crt.compare_identity(boto3_creds, crt_creds_wrapper)\n            is matching\n        )\n\n    @requires_crt()\n    def test_compare_idenities_no_credentials(self):\n        def no_credentials():\n            raise botocore.exceptions.NoCredentialsError()\n\n        boto3_creds = Credentials("access", "secret", "token")\n        crt_creds_wrapper = no_credentials\n        assert (\n            boto3.crt.compare_identity(boto3_creds, crt_creds_wrapper) is False\n        )\n\n    @requires_crt()\n    def test_get_crt_s3_client(\n        self,\n        mock_crt_process_lock,\n        mock_crt_client_singleton,\n        mock_serializer_singleton,\n    ):\n        config = TransferConfig()\n        crt_s3_client = boto3.crt.get_crt_s3_client(USW2_S3_CLIENT, config)\n        assert isinstance(crt_s3_client, boto3.crt.CRTS3Client)\n        assert isinstance(crt_s3_client.process_lock, CrossProcessLockClass)\n        assert crt_s3_client.region == "us-west-2"\n        assert isinstance(\n            crt_s3_client.cred_provider, BotocoreCRTCredentialsWrapper\n        )\n\n    @requires_crt()\n    def test_get_crt_s3_client_w_wrong_region(\n        self,\n        mock_crt_process_lock,\n        mock_crt_client_singleton,\n        mock_serializer_singleton,\n    ):\n        config = TransferConfig()\n        crt_s3_client = boto3.crt.get_crt_s3_client(USW2_S3_CLIENT, config)\n        assert isinstance(crt_s3_client, boto3.crt.CRTS3Client)\n\n        # Ensure we don\'t create additional CRT clients\n        use1_crt_s3_client = boto3.crt.get_crt_s3_client(\n            USE1_S3_CLIENT, config\n        )\n        assert use1_crt_s3_client is crt_s3_client\n        assert use1_crt_s3_client.region == "us-west-2"\n\n    @requires_crt()\n    @mock.patch(\'boto3.crt.TRANSFER_CONFIG_SUPPORTS_CRT\', False)\n    def test_config_without_crt_support_emits_warning(\n        self,\n        mock_crt_process_lock,\n        mock_crt_client_singleton,\n        mock_serializer_singleton,\n        caplog,\n    ):\n        config = TransferConfig()\n        boto3.crt.create_crt_transfer_manager(USW2_S3_CLIENT, config)\n        assert any(\n            [\n                \'requires s3transfer >= 0.16.0\' in r.message\n                for r in caplog.records\n            ]\n        )\n',
        }
