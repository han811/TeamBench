"""
Parameterized generator for GH893_ray_23190.

Source PR:    https://github.com/ray-project/ray/pull/23190
Source Issue: https://github.com/ray-project/ray/issues/1234

Seed varies: renames 'base' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH893_ray_23190'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH893_ray_23190'
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
                files[fpath] = files[fpath].replace('base', 'base' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH893_ray_23190',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'ray-project/ray',
                "pr_number": 23190,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/ray-project/ray/pull/23190",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'python/ray/workflow/storage/__init__.py': 'import logging\nimport urllib.parse as parse\nfrom ray.workflow.storage.base import Storage\nfrom ray.workflow.storage.base import DataLoadError, DataSaveError, KeyNotFoundError\n\nlogger = logging.getLogger(__name__)\n\n\ndef create_storage(storage_url: str) -> Storage:\n    """A factory function that creates different type of storage according\n    to the URL.\n\n    Args:\n        storage_url: A URL indicates the storage type and root path.\n        Currently only two types of storages are supported: local fs and s3\n        For local fs, a path is needed, it can be either a URI with scheme\n        file:// or just a local path, i.e.:\n           file:///local_path\n           local_path\n\n        For s3, bucket, path are necessary. In the meantime, other parameters\n        can be passed as well, like credientials or regions, i.e.:\n           s3://bucket/path?region_name=str&endpoint_url=str&aws_access_key_id=str&\n               aws_secret_access_key=str&aws_session_token=str\n\n        All parameters are optional and have the same meaning as boto3.client\n\n    Returns:\n        A storage instance.\n    """\n    parsed_url = parse.urlparse(storage_url)\n    if parsed_url.scheme == "file" or parsed_url.scheme == "":\n        from ray.workflow.storage.filesystem import FilesystemStorageImpl\n\n        return FilesystemStorageImpl(parsed_url.path)\n    elif parsed_url.scheme == "s3":\n        from ray.workflow.storage.s3 import S3StorageImpl\n\n        bucket = parsed_url.netloc\n        s3_path = parsed_url.path.lstrip("/")\n        if not s3_path:\n            raise ValueError(f"Invalid s3 path: {s3_path}")\n        params = dict(parse.parse_qsl(parsed_url.query))\n        return S3StorageImpl(bucket, s3_path, **params)\n    elif parsed_url.scheme == "debug":\n        from ray.workflow.storage.debug import DebugStorage\n\n        params = dict(parse.parse_qsl(parsed_url.query))\n        return DebugStorage(create_storage(params["storage"]), path=parsed_url.path)\n    else:\n        raise ValueError(f"Invalid url: {storage_url}")\n\n\n# the default storage is a local filesystem storage with a hidden directory\n_global_storage = None\n\n\ndef get_global_storage() -> Storage:\n    global _global_storage\n    if _global_storage is None:\n        raise RuntimeError(\n            "`workflow.init()` must be called prior to " "using the workflows API."\n        )\n    return _global_storage\n\n\ndef set_global_storage(storage: Storage) -> None:\n    global _global_storage\n    _global_storage = storage\n\n\n__all__ = (\n    "Storage",\n    "get_global_storage",\n    "create_storage",\n    "set_global_storage",\n    "DataLoadError",\n    "DataSaveError",\n    "KeyNotFoundError",\n)\n',
            'python/ray/workflow/tests/test_basic_workflows.py': 'import time\n\nfrom ray.tests.conftest import *  # noqa\n\nimport pytest\nimport ray\nfrom ray import workflow\nfrom ray.workflow import workflow_access\n\n\n@workflow.step\ndef identity(x):\n    return x\n\n\n@workflow.step\ndef source1():\n    return "[source1]"\n\n\n@workflow.step\ndef append1(x):\n    return x + "[append1]"\n\n\n@workflow.step\ndef append2(x):\n    return x + "[append2]"\n\n\n@workflow.step\ndef simple_sequential():\n    x = source1.step()\n    y = append1.step(x)\n    return append2.step(y)\n\n\n@workflow.step\ndef simple_sequential_with_input(x):\n    y = append1.step(x)\n    return append2.step(y)\n\n\n@workflow.step\ndef loop_sequential(n):\n    x = source1.step()\n    for _ in range(n):\n        x = append1.step(x)\n    return append2.step(x)\n\n\n@workflow.step\ndef nested_step(x):\n    return append2.step(append1.step(x + "~[nested]~"))\n\n\n@workflow.step\ndef nested(x):\n    return nested_step.step(x)\n\n\n@workflow.step\ndef join(x, y):\n    return f"join({x}, {y})"\n\n\n@workflow.step\ndef fork_join():\n    x = source1.step()\n    y = append1.step(x)\n    y = identity.step(y)\n    z = append2.step(x)\n    return join.step(y, z)\n\n\n@workflow.step\ndef blocking():\n    time.sleep(10)\n    return 314\n\n\n@workflow.step\ndef mul(a, b):\n    return a * b\n\n\n@workflow.step\ndef factorial(n):\n    if n == 1:\n        return 1\n    else:\n        return mul.step(n, factorial.step(n - 1))\n\n\ndef test_basic_workflows(workflow_start_regular_shared):\n    # This test also shows different "style" of running workflows.\n    assert simple_sequential.step().run() == "[source1][append1][append2]"\n\n    wf = simple_sequential_with_input.step("start:")\n    assert wf.run() == "start:[append1][append2]"\n\n    wf = loop_sequential.step(3)\n    assert wf.run() == "[source1]" + "[append1]" * 3 + "[append2]"\n\n    wf = nested.step("nested:")\n    assert wf.run() == "nested:~[nested]~[append1][append2]"\n\n    wf = fork_join.step()\n    assert wf.run() == "join([source1][append1], [source1][append2])"\n\n    assert factorial.step(10).run() == 3628800\n\n\ndef test_async_execution(workflow_start_regular_shared):\n    start = time.time()\n    output = blocking.step().run_async()\n    duration = time.time() - start\n    assert duration < 5  # workflow.run is not blocked\n    assert ray.get(output) == 314\n\n\ndef test_partial(workflow_start_regular_shared):\n    ys = [1, 2, 3]\n\n    def add(x, y):\n        return x + y\n\n    from functools import partial\n\n    f1 = workflow.step(partial(add, 10)).step(10)\n\n    assert "__anonymous_func__" in f1._name\n    assert f1.run() == 20\n\n    fs = [partial(add, y=y) for y in ys]\n\n    @ray.workflow.step\n    def chain_func(*args, **kw_argv):\n        # Get the first function as a start\n        wf_step = workflow.step(fs[0]).step(*args, **kw_argv)\n        for i in range(1, len(fs)):\n            # Convert each function inside steps into workflow step\n            # function and then use the previous output as the input\n            # for them.\n            wf_step = workflow.step(fs[i]).step(wf_step)\n        return wf_step\n\n    assert chain_func.step(1).run() == 7\n\n\n@ray.remote\ndef deep_nested(x):\n    if x >= 42:\n        return x\n    return deep_nested.remote(x + 1)\n\n\ndef _resolve_workflow_output(workflow_id: str, output: ray.ObjectRef):\n    while isinstance(output, ray.ObjectRef):\n        output = ray.get(output)\n    return output\n\n\ndef test_workflow_output_resolving(workflow_start_regular_shared):\n    # deep nested workflow\n    nested_ref = deep_nested.remote(30)\n    original_func = workflow_access._resolve_workflow_output\n    # replace the original function with a new function that does not\n    # involving named actor\n    workflow_access._resolve_workflow_output = _resolve_workflow_output\n    try:\n        ref = workflow_access.flatten_workflow_output("fake_workflow_id", nested_ref)\n    finally:\n        # restore the function\n        workflow_access._resolve_workflow_output = original_func\n    assert ray.get(ref) == 42\n\n\ndef test_run_or_resume_during_running(workflow_start_regular_shared):\n    output = simple_sequential.step().run_async(workflow_id="running_workflow")\n    with pytest.raises(RuntimeError):\n        simple_sequential.step().run_async(workflow_id="running_workflow")\n    with pytest.raises(RuntimeError):\n        workflow.resume(workflow_id="running_workflow")\n    assert ray.get(output) == "[source1][append1][append2]"\n\n\ndef test_step_failure(workflow_start_regular_shared, tmp_path):\n    (tmp_path / "test").write_text("0")\n\n    @workflow.step\n    def unstable_step():\n        v = int((tmp_path / "test").read_text())\n        (tmp_path / "test").write_text(f"{v + 1}")\n        if v < 10:\n            raise ValueError("Invalid")\n        return v\n\n    with pytest.raises(Exception):\n        unstable_step.options(max_retries=-1).step().run()\n\n    with pytest.raises(Exception):\n        unstable_step.options(max_retries=3).step().run()\n    assert 10 == unstable_step.options(max_retries=8).step().run()\n    (tmp_path / "test").write_text("0")\n    (ret, err) = (\n        unstable_step.options(max_retries=3, catch_exceptions=True).step().run()\n    )\n    assert ret is None\n    assert isinstance(err, ValueError)\n    (ret, err) = (\n        unstable_step.options(max_retries=8, catch_exceptions=True).step().run()\n    )\n    assert ret == 10\n    assert err is None\n\n\ndef test_step_failure_decorator(workflow_start_regular_shared, tmp_path):\n    (tmp_path / "test").write_text("0")\n\n    @workflow.step(max_retries=11)\n    def unstable_step():\n        v = int((tmp_path / "test").read_text())\n        (tmp_path / "test").write_text(f"{v + 1}")\n        if v < 10:\n            raise ValueError("Invalid")\n        return v\n\n    assert unstable_step.step().run() == 10\n\n    (tmp_path / "test").write_text("0")\n\n    @workflow.step(catch_exceptions=True)\n    def unstable_step_exception():\n        v = int((tmp_path / "test").read_text())\n        (tmp_path / "test").write_text(f"{v + 1}")\n        if v < 10:\n            raise ValueError("Invalid")\n        return v\n\n    (ret, err) = unstable_step_exception.step().run()\n    assert ret is None\n    assert err is not None\n\n    (tmp_path / "test").write_text("0")\n\n    @workflow.step(catch_exceptions=True, max_retries=4)\n    def unstable_step_exception():\n        v = int((tmp_path / "test").read_text())\n        (tmp_path / "test").write_text(f"{v + 1}")\n        if v < 10:\n            raise ValueError("Invalid")\n        return v\n\n    (ret, err) = unstable_step_exception.step().run()\n    assert ret is None\n    assert err is not None\n    assert (tmp_path / "test").read_text() == "4"\n\n\ndef test_nested_catch_exception(workflow_start_regular_shared, tmp_path):\n    @workflow.step\n    def f2():\n        return 10\n\n    @workflow.step\n    def f1():\n        return f2.step()\n\n    assert (10, None) == f1.options(catch_exceptions=True).step().run()\n\n\ndef test_nested_catch_exception_2(workflow_start_regular_shared, tmp_path):\n    @workflow.step\n    def f1(n):\n        if n == 0:\n            raise ValueError()\n        else:\n            return f1.step(n - 1)\n\n    ret, err = f1.options(catch_exceptions=True).step(5).run()\n    assert ret is None\n    assert isinstance(err, ValueError)\n\n\ndef test_dynamic_output(workflow_start_regular_shared):\n    @workflow.step\n    def exponential_fail(k, n):\n        if n > 0:\n            if n < 3:\n                raise Exception("Failed intentionally")\n            return exponential_fail.options(name=f"step_{n}").step(k * 2, n - 1)\n        return k\n\n    # When workflow fails, the dynamic output should points to the\n    # latest successful step.\n    try:\n        exponential_fail.options(name="step_0").step(3, 10).run(\n            workflow_id="dynamic_output"\n        )\n    except Exception:\n        pass\n    from ray.workflow.workflow_storage import get_workflow_storage\n\n    wf_storage = get_workflow_storage(workflow_id="dynamic_output")\n    result = wf_storage.inspect_step("step_0")\n    assert result.output_step_id == "step_3"\n\n\nif __name__ == "__main__":\n    import sys\n\n    sys.exit(pytest.main(["-v", __file__]))\n',
        }
