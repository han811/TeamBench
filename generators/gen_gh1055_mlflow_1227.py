"""
Parameterized generator for GH1055_mlflow_1227.

Source PR:    https://github.com/mlflow/mlflow/pull/1227
Source Issue: N/A

Seed varies: renames 'actual_result' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH1055_mlflow_1227'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH1055_mlflow_1227'
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
                files[fpath] = files[fpath].replace('actual_result', 'actual_result' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH1055_mlflow_1227',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'mlflow/mlflow',
                "pr_number": 1227,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/mlflow/mlflow/pull/1227",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'mlflow/tracking/artifact_utils.py': '"""\nUtilities for dealing with artifacts in the context of a Run.\n"""\nimport posixpath\n\nfrom six.moves import urllib\n\nfrom mlflow.exceptions import MlflowException\nfrom mlflow.protos.databricks_pb2 import INVALID_PARAMETER_VALUE\nfrom mlflow.store.artifact_repository_registry import get_artifact_repository\nfrom mlflow.tracking.utils import _get_store\n\n\ndef get_artifact_uri(run_id, artifact_path=None):\n    """\n    Get the absolute URI of the specified artifact in the specified run. If `path` is not specified,\n    the artifact root URI of the specified run will be returned; calls to ``log_artifact``\n    and ``log_artifacts`` write artifact(s) to subdirectories of the artifact root URI.\n\n    :param run_id: The ID of the run for which to obtain an absolute artifact URI.\n    :param artifact_path: The run-relative artifact path. For example,\n                          ``path/to/artifact``. If unspecified, the artifact root URI for the\n                          specified run will be returned.\n    :return: An *absolute* URI referring to the specified artifact or the specified run\'s artifact\n             root. For example, if an artifact path is provided and the specified run uses an\n             S3-backed  store, this may be a uri of the form\n             ``s3://<bucket_name>/path/to/artifact/root/path/to/artifact``. If an artifact path\n             is not provided and the specified run uses an S3-backed store, this may be a URI of\n             the form ``s3://<bucket_name>/path/to/artifact/root``.\n    """\n    if not run_id:\n        raise MlflowException(\n            message="A run_id must be specified in order to obtain an artifact uri!",\n            error_code=INVALID_PARAMETER_VALUE)\n\n    store = _get_store()\n    run = store.get_run(run_id)\n    # Maybe move this method to RunsArtifactRepository so the circular dependency is clearer.\n    assert urllib.parse.urlparse(run.info.artifact_uri).scheme != "runs"  # avoid an infinite loop\n    if artifact_path is None:\n        return run.info.artifact_uri\n    else:\n        return posixpath.join(run.info.artifact_uri, artifact_path)\n\n\n# TODO: This method does not require a Run and its internals should be moved to\n#  data.download_uri (requires confirming that Projects will not break with this change).\n# Also this would be much simpler if artifact_repo.download_artifacts could take the absolute path\n# or no path.\ndef _download_artifact_from_uri(artifact_uri, output_path=None):\n    """\n    :param artifact_uri: The *absolute* URI of the artifact to download.\n    :param output_path: The local filesystem path to which to download the artifact. If unspecified,\n                        a local output path will be created.\n    """\n    artifact_src_dir = posixpath.dirname(artifact_uri)\n    artifact_src_relative_path = posixpath.basename(artifact_uri)\n    artifact_repo = get_artifact_repository(artifact_uri=artifact_src_dir)\n    return artifact_repo.download_artifacts(artifact_path=artifact_src_relative_path,\n                                            dst_path=output_path)\n',
            'tests/store/test_cli.py': 'import json\nimport os\nimport posixpath\n\nimport mlflow\nimport mlflow.pyfunc\nfrom mlflow.entities import FileInfo\nfrom mlflow.store.cli import _file_infos_to_json\nfrom mlflow.utils.file_utils import TempDir\nfrom subprocess import Popen, STDOUT, PIPE\n\n\ndef test_file_info_to_json():\n    file_infos = [\n        FileInfo("/my/file", False, 123),\n        FileInfo("/my/dir", True, None),\n    ]\n    info_str = _file_infos_to_json(file_infos)\n    assert json.loads(info_str) == [{\n        "path": "/my/file",\n        "is_dir": False,\n        "file_size": "123",\n    }, {\n        "path": "/my/dir",\n        "is_dir": True,\n    }]\n\n\ndef test_download_artifacts_from_uri():\n    with mlflow.start_run() as run:\n        with TempDir() as tmp:\n            local_path = tmp.path("test")\n            with open(local_path, "w") as f:\n                f.write("test")\n            mlflow.log_artifact(local_path, "test")\n    command = ["mlflow", "artifacts", "download-from-uri", "-a"]\n    # Test with run uri\n    run_uri = "runs:/{run_id}/test".format(run_id=run.info.run_id)\n    actual_uri = posixpath.join(run.info.artifact_uri, "test")\n    for uri in (run_uri, actual_uri):\n        p = Popen(command + [uri], stdout=PIPE,\n                  stderr=STDOUT)\n        output = p.stdout.readlines()\n        downloaded_file_path = output[-1].strip()\n        downloaded_file = os.listdir(downloaded_file_path)[0]\n        with open(os.path.join(downloaded_file_path, downloaded_file), "r") as f:\n            assert f.read() == "test"\n',
        }
