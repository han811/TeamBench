"""
Parameterized generator for GH942_great_expectati_8087.

Source PR:    https://github.com/great-expectations/great_expectations/pull/8087
Source Issue: N/A

Seed varies: renames 'cloud_ref' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH942_great_expectati_8087'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH942_great_expectati_8087'
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
                files[fpath] = files[fpath].replace('cloud_ref', 'cloud_ref' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH942_great_expectati_8087',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'great-expectations/great_expectations',
                "pr_number": 8087,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/great-expectations/great_expectations/pull/8087",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'tests/data_context/cloud_data_context/test_include_rendered_content.py': 'import random\nimport string\nfrom unittest import mock\n\nimport pandas as pd\nimport pytest\nimport responses\n\nfrom great_expectations.core import (\n    ExpectationConfiguration,\n    ExpectationSuite,\n    ExpectationValidationResult,\n)\nfrom great_expectations.data_context import CloudDataContext\nfrom great_expectations.data_context.cloud_constants import GXCloudRESTResource\nfrom great_expectations.data_context.types.refs import GXCloudResourceRef\nfrom great_expectations.render import RenderedAtomicContent\nfrom great_expectations.validator.validator import Validator\n\n\n@pytest.mark.cloud\n@responses.activate\ndef test_cloud_backed_data_context_add_or_update_expectation_suite_include_rendered_content(\n    empty_cloud_data_context: CloudDataContext,\n) -> None:\n    """\n    Cloud-backed contexts should save an ExpectationSuite with rendered_content by default.\n    """\n    context = empty_cloud_data_context\n\n    ge_cloud_id = "d581305a-cdce-483b-84ba-5c673d2ce009"\n    cloud_ref = GXCloudResourceRef(\n        resource_type=GXCloudRESTResource.EXPECTATION_SUITE,\n        id=ge_cloud_id,\n        url="foo/bar/baz",\n        # response_json will not be empty but is not needed for this test.\n        response_json={},\n    )\n\n    empty_expectation_suite = ExpectationSuite(expectation_suite_name="test_suite")\n    with mock.patch(\n        "great_expectations.data_context.store.gx_cloud_store_backend.GXCloudStoreBackend.has_key"\n    ), mock.patch(\n        "great_expectations.data_context.store.gx_cloud_store_backend.GXCloudStoreBackend._set",\n        return_value=cloud_ref,\n    ), mock.patch(\n        "great_expectations.data_context.data_context.CloudDataContext.get_expectation_suite",\n        return_value=empty_expectation_suite,\n    ):\n        expectation_suite: ExpectationSuite = context.add_or_update_expectation_suite(\n            "test_suite"\n        )\n    expectation_suite.expectations.append(\n        ExpectationConfiguration(\n            expectation_type="expect_table_row_count_to_equal", kwargs={"value": 10}\n        )\n    )\n    assert expectation_suite.expectations[0].rendered_content is None\n\n    with mock.patch(\n        "great_expectations.data_context.store.gx_cloud_store_backend.GXCloudStoreBackend.list_keys"\n    ), mock.patch(\n        "great_expectations.data_context.store.gx_cloud_store_backend.GXCloudStoreBackend._set"\n    ) as mock_update:\n        context.save_expectation_suite(expectation_suite=expectation_suite)\n\n        # remove dynamic great_expectations version\n        mock_update.call_args[0][1].pop("meta")\n\n        assert mock_update.call_args[0][1] == {\n            "expectation_suite_name": "test_suite",\n            "ge_cloud_id": None,\n            "data_asset_type": None,\n            "expectations": [\n                {\n                    "rendered_content": [\n                        {\n                            "value": {\n                                "template": "Must have exactly $value rows.",\n                                "params": {\n                                    "value": {"schema": {"type": "number"}, "value": 10}\n                                },\n                                "schema": {\n                                    "type": "com.superconductive.rendered.string"\n                                },\n                            },\n                            "value_type": "StringValueType",\n                            "name": "atomic.prescriptive.summary",\n                        }\n                    ],\n                    "expectation_type": "expect_table_row_count_to_equal",\n                    "meta": {},\n                    "kwargs": {"value": 10},\n                }\n            ],\n        }\n\n\n@pytest.mark.cloud\n@pytest.mark.integration\ndef test_cloud_backed_data_context_expectation_validation_result_include_rendered_content(\n    empty_cloud_data_context: CloudDataContext,\n) -> None:\n    """\n    All CloudDataContexts should save an ExpectationValidationResult with rendered_content by default.\n    """\n    context = empty_cloud_data_context\n\n    df = pd.DataFrame([1, 2, 3, 4, 5])\n    suite_name = f"test_suite_{\'\'.join(random.choice(string.ascii_letters + string.digits) for _ in range(8))}"\n    mock_datasource_get_response = {\n        "data": {\n            "id": "123456",\n            "attributes": {\n                "datasource_config": {},\n            },\n        },\n    }\n\n    with mock.patch(\n        "great_expectations.data_context.store.gx_cloud_store_backend.GXCloudStoreBackend.has_key",\n        return_value=False,\n    ), mock.patch(\n        "great_expectations.data_context.store.gx_cloud_store_backend.GXCloudStoreBackend.set"\n    ), mock.patch(\n        "great_expectations.data_context.store.gx_cloud_store_backend.GXCloudStoreBackend.get",\n        return_value=mock_datasource_get_response,\n    ):\n        data_asset = context.sources.pandas_default.add_dataframe_asset(\n            name="my_dataframe_asset",\n            dataframe=df,\n        )\n        validator: Validator = context.get_validator(\n            batch_request=data_asset.build_batch_request(),\n            create_expectation_suite_with_name=suite_name,\n        )\n\n        expectation_validation_result: ExpectationValidationResult = (\n            validator.expect_table_row_count_to_equal(value=10)\n        )\n\n    for rendered_content in expectation_validation_result.rendered_content:\n        assert isinstance(rendered_content, RenderedAtomicContent)\n\n    for (\n        rendered_content\n    ) in expectation_validation_result.expectation_config.rendered_content:\n        assert isinstance(rendered_content, RenderedAtomicContent)\n',
        }
