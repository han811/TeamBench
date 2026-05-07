"""
Parameterized generator for GH1211_wandb_11240.

Source PR:    https://github.com/wandb/wandb/pull/11240
Source Issue: N/A

Seed varies: renames 'base_url' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH1211_wandb_11240'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH1211_wandb_11240'
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
                files[fpath] = files[fpath].replace('base_url', 'base_url' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH1211_wandb_11240',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'wandb/wandb',
                "pr_number": 11240,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/wandb/wandb/pull/11240",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'tests/unit_tests/test_wandb_run.py': 'import copy\nimport platform\n\nimport numpy as np\nimport pytest\nimport wandb\nfrom wandb.apis import public\nfrom wandb.sdk import wandb_run\n\nREFERENCE_ATTRIBUTES = set(\n    [\n        "alert",\n        "config",\n        "config_static",\n        "define_metric",\n        "dir",\n        "disabled",\n        "display",\n        "entity",\n        "finish",\n        "finish_artifact",\n        "get_project_url",\n        "get_sweep_url",\n        "get_url",\n        "group",\n        "id",\n        "job_type",\n        "link_artifact",\n        "link_model",\n        "log",\n        "log_artifact",\n        "log_code",\n        "log_model",\n        "mark_preempting",\n        "name",\n        "notes",\n        "offline",\n        "path",\n        "project",\n        "project_name",\n        "project_url",\n        "restore",\n        "resumed",\n        "save",\n        "settings",\n        "start_time",\n        "starting_step",\n        "status",\n        "step",\n        "summary",\n        "sweep_id",\n        "sweep_url",\n        "tags",\n        "to_html",\n        "unwatch",\n        "upsert_artifact",\n        "url",\n        "use_artifact",\n        "use_model",\n        "watch",\n    ]\n)\n\n\ndef test_run_step_property(mock_run):\n    run = mock_run()\n    run.log(dict(this=1))\n    run.log(dict(this=2))\n    assert run.step == 2\n\n\ndef test_log_avoids_mutation(mock_run):\n    run = mock_run()\n    d = dict(this=1)\n    run.log(d)\n    assert d == dict(this=1)\n\n\ndef test_display(mock_run):\n    run = mock_run(settings=wandb.Settings(mode="offline"))\n    assert run.display() is False\n\n\n@pytest.mark.parametrize(\n    "config, sweep_config, expected_config",\n    [\n        (\n            dict(param1=2, param2=4),\n            dict(),\n            dict(param1=2, param2=4),\n        ),\n        (\n            dict(param1=2, param2=4),\n            dict(param3=9),\n            dict(param1=2, param2=4, param3=9),\n        ),\n        (\n            dict(param1=2, param2=4),\n            dict(param2=8, param3=9),\n            dict(param1=2, param2=8, param3=9),\n        ),\n    ],\n)\ndef test_run_config(mock_run, config, sweep_config, expected_config):\n    run = mock_run(config=config, sweep_config=sweep_config)\n    assert dict(run.config) == expected_config\n\n\ndef test_run_urls(mock_run):\n    base_url = "https://my.cool.site.com"\n    entity = "me"\n    project = "lol"\n    run_id = "my-run"\n    run = mock_run(\n        settings=wandb.Settings(\n            base_url=base_url,\n            entity=entity,\n            project=project,\n            run_id=run_id,\n        )\n    )\n    assert run.get_project_url() == f"{base_url}/{entity}/{project}"\n    assert run.get_url() == f"{base_url}/{entity}/{project}/runs/{run.id}"\n\n\ndef test_run_publish_config(mock_run, parse_records, record_q):\n    run = mock_run()\n    run.config.t = 1\n    run.config.t2 = 2\n\n    parsed = parse_records(record_q)\n\n    assert len(parsed.records) == 2\n    assert len(parsed.summary) == 0\n\n    config = parsed.config\n    assert len(config) == 2\n    assert config[0]["t"] == "1"\n    assert config[1]["t2"] == "2"\n\n\ndef test_run_publish_history(mock_run, parse_records, record_q):\n    run = mock_run()\n    run.log(dict(this=1))\n    run.log(dict(that=2))\n\n    parsed = parse_records(record_q)\n\n    assert len(parsed.records) == 2\n    assert len(parsed.summary) == 0\n\n    history = parsed.history or parsed.partial_history\n    assert len(history) == 2\n    assert history[0]["this"] == "1"\n    assert history[1]["that"] == "2"\n\n\n@pytest.mark.skipif(\n    platform.system() == "Windows",\n    reason="numpy.float128 does not exist on windows",\n)\n@pytest.mark.skipif(\n    platform.system() == "Darwin" and platform.machine() == "arm64",\n    reason="numpy.float128 does not exist on Macs with the Apple M1 chip",\n)\n# @pytest.mark.GH2255 #TODO think of a marker format for tests that fix reported issues\ndef test_numpy_high_precision_float_downcasting(mock_run, parse_records, record_q):\n    run = mock_run()\n    run.log(dict(this=np.float128(0.0)))\n\n    parsed = parse_records(record_q)\n\n    assert len(parsed.records) == 1\n    assert len(parsed.summary) == 0\n\n    history = parsed.history or parsed.partial_history\n    assert len(history) == 1\n    assert history[0]["this"] == "0.0"\n\n\ndef test_mark_preempting(mock_run, parse_records, record_q):\n    run = mock_run()\n    run.log(dict(this=1))\n    run.log(dict(that=2))\n    run.mark_preempting()\n\n    parsed = parse_records(record_q)\n\n    assert len(parsed.records) == 3\n\n    assert len(parsed.preempting) == 1\n    assert parsed.records[-1].HasField("preempting")\n\n\ndef test_run_pub_config(mock_run, record_q, parse_records):\n    run = mock_run()\n    run.config.t = 1\n    run.config.t2 = 2\n\n    parsed = parse_records(record_q)\n    assert len(parsed.records) == 2\n    assert len(parsed.summary) == 0\n    assert len(parsed.config) == 2\n    assert parsed.config[0]["t"] == "1"\n    assert parsed.config[1]["t2"] == "2"\n\n\ndef test_run_pub_history(mock_run, record_q, parse_records):\n    run = mock_run()\n    run.log(dict(this=1))\n    run.log(dict(that=2))\n\n    parsed = parse_records(record_q)\n    assert len(parsed.records) == 2\n    assert len(parsed.summary) == 0\n    history = parsed.history or parsed.partial_history\n    assert len(history) == 2\n    assert history[0]["this"] == "1"\n    assert history[1]["that"] == "2"\n\n\ndef test_use_artifact_offline(mock_run):\n    run = mock_run(settings=wandb.Settings(mode="offline"))\n    with pytest.raises(Exception) as e_info:\n        run.use_artifact("boom-data")\n        assert str(e_info.value) == "Cannot use artifact when in offline mode."\n\n\ndef test_run_basic():\n    s = wandb.Settings()\n    c = dict(\n        param1=2,\n        param2=4,\n        param3=set(range(10)),\n        param4=list(range(10, 20)),\n        param5=tuple(range(20, 30)),\n        dict_param=dict(\n            a=list(range(10)), b=tuple(range(10, 20)), c=set(range(20, 30))\n        ),\n    )\n    run = wandb_run.Run(settings=s, config=c)\n    assert dict(run.config) == dict(\n        param1=2,\n        param2=4,\n        param3=list(range(10)),\n        param4=list(range(10, 20)),\n        param5=list(range(20, 30)),\n        dict_param=dict(\n            a=list(range(10)), b=list(range(10, 20)), c=list(range(20, 30))\n        ),\n    )\n\n\ndef test_run_sweep():\n    s = wandb.Settings()\n    c = dict(param1=2, param2=4)\n    sw = dict(param3=9)\n    run = wandb_run.Run(settings=s, config=c, sweep_config=sw)\n    assert dict(run.config) == dict(param1=2, param2=4, param3=9)\n\n\ndef test_run_sweep_overlap():\n    s = wandb.Settings()\n    c = dict(param1=2, param2=4)\n    sw = dict(param2=8, param3=9)\n    run = wandb_run.Run(settings=s, config=c, sweep_config=sw)\n    assert dict(run.config) == dict(param1=2, param2=8, param3=9)\n\n\ndef test_run_deepcopy():\n    s = wandb.Settings()\n    c = dict(param1=2, param2=4)\n    run = wandb_run.Run(settings=s, config=c)\n    run2 = copy.deepcopy(run)\n    assert id(run) == id(run2)\n\n\n@pytest.mark.parametrize(\n    "settings, expected",\n    [\n        ({}, False),\n        ({"resume": False}, False),\n        ({"resume": True}, True),\n        ({"resume": "auto"}, True),\n        ({"resume": "allow"}, True),\n        ({"resume": "never"}, True),\n        ({"resume": "must"}, True),\n    ],\n)\ndef test_resumed_run_resume_file_state(mocker, mock_run, tmp_path, settings, expected):\n    tmp_file = tmp_path / "test_resume.json"\n    tmp_file.write_text("{\'run_id\': \'test\'}")\n\n    mocker.patch("wandb.sdk.wandb_settings.Settings.resume_fname", tmp_file)\n\n    run = mock_run(use_magic_mock=True, settings=settings)\n    run._on_ready()\n\n    assert tmp_file.exists() == expected\n\n\ndef test_new_attributes(mock_run):\n    run = mock_run()\n    current_attributes = set([attr for attr in dir(run) if not attr.startswith("_")])\n    added_attributes = current_attributes - REFERENCE_ATTRIBUTES\n    removed_attributes = REFERENCE_ATTRIBUTES - current_attributes\n    assert not added_attributes, f"New attributes: {added_attributes}"\n    assert not removed_attributes, f"Removed attributes: {removed_attributes}"\n\n\ndef test_public_api_uses_api_key(mock_run, mocker):\n    api_key = "anything"\n\n    mock_api_class = mocker.patch.object(public, "Api")\n    mock_api_instance = mocker.MagicMock()\n    mock_api_class.return_value = mock_api_instance\n    run = mock_run(settings=wandb.Settings(api_key=api_key))\n\n    api = run._public_api()\n\n    mock_api_class.assert_called_once_with(\n        # overrides from mock_run\n        {\n            "run": None,\n            "entity": "",\n            "project": "",\n        },\n        api_key=api_key,\n    )\n    assert api is mock_api_instance\n\n\ndef test_public_api_is_cached(mock_run, mocker):\n    mock_api_class = mocker.patch.object(public, "Api")\n    mock_api_instance = mocker.MagicMock()\n    mock_api_class.return_value = mock_api_instance\n    run = mock_run()\n\n    api1 = run._public_api()\n    api2 = run._public_api()\n\n    assert api1 is api2\n    assert api1 is run._cached_public_api\n    mock_api_class.assert_called_once()\n',
        }
