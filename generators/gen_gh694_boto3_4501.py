"""
Parameterized generator for GH694_boto3_4501.

Source PR:    https://github.com/boto/boto3/pull/4501
Source Issue: N/A

Seed varies: renames 'collections' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH694_boto3_4501'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH694_boto3_4501'
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
                files[fpath] = files[fpath].replace('collections', 'collections' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH694_boto3_4501',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'boto/boto3',
                "pr_number": 4501,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/boto/boto3/pull/4501",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'boto3/utils.py': '# Copyright 2015 Amazon.com, Inc. or its affiliates. All Rights Reserved.\n#\n# Licensed under the Apache License, Version 2.0 (the "License"). You\n# may not use this file except in compliance with the License. A copy of\n# the License is located at\n#\n# https://aws.amazon.com/apache2.0/\n#\n# or in the "license" file accompanying this file. This file is\n# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF\n# ANY KIND, either express or implied. See the License for the specific\n# language governing permissions and limitations under the License.\nimport sys\nfrom collections import namedtuple\n\n_ServiceContext = namedtuple(\n    \'ServiceContext\',\n    [\n        \'service_name\',\n        \'service_model\',\n        \'service_waiter_model\',\n        \'resource_json_definitions\',\n    ],\n)\n\n\nclass ServiceContext(_ServiceContext):\n    """Provides important service-wide, read-only information about a service\n\n    :type service_name: str\n    :param service_name: The name of the service\n\n    :type service_model: :py:class:`botocore.model.ServiceModel`\n    :param service_model: The model of the service.\n\n    :type service_waiter_model: :py:class:`botocore.waiter.WaiterModel` or\n        a waiter model-like object such as\n        :py:class:`boto3.utils.LazyLoadedWaiterModel`\n    :param service_waiter_model: The waiter model of the service.\n\n    :type resource_json_definitions: dict\n    :param resource_json_definitions: The loaded json models of all resource\n        shapes for a service. It is equivalient of loading a\n        ``resource-1.json`` and retrieving the value at the key "resources".\n    """\n\n    pass\n\n\ndef import_module(name):\n    """Import module given a name.\n\n    Does not support relative imports.\n\n    """\n    __import__(name)\n    return sys.modules[name]\n\n\ndef lazy_call(full_name, **kwargs):\n    parent_kwargs = kwargs\n\n    def _handler(**kwargs):\n        module, function_name = full_name.rsplit(\'.\', 1)\n        module = import_module(module)\n        kwargs.update(parent_kwargs)\n        return getattr(module, function_name)(**kwargs)\n\n    return _handler\n\n\ndef inject_attribute(class_attributes, name, value):\n    if name in class_attributes:\n        raise RuntimeError(\n            f\'Cannot inject class attribute "{name}", attribute \'\n            f\'already exists in class dict.\'\n        )\n    else:\n        class_attributes[name] = value\n\n\nclass LazyLoadedWaiterModel:\n    """A lazily loaded waiter model\n\n    This does not load the service waiter model until an attempt is made\n    to retrieve the waiter model for a specific waiter. This is helpful\n    in docstring generation where we do not need to actually need to grab\n    the waiter-2.json until it is accessed through a ``get_waiter`` call\n    when the docstring is generated/accessed.\n    """\n\n    def __init__(self, bc_session, service_name, api_version):\n        self._session = bc_session\n        self._service_name = service_name\n        self._api_version = api_version\n\n    def get_waiter(self, waiter_name):\n        return self._session.get_waiter_model(\n            self._service_name, self._api_version\n        ).get_waiter(waiter_name)\n',
        }
