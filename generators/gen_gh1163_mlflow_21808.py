"""
Parameterized generator for GH1163_mlflow_21808.

Source PR:    https://github.com/mlflow/mlflow/pull/21808
Source Issue: N/A

Seed varies: renames 'break' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH1163_mlflow_21808'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH1163_mlflow_21808'
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
                files[fpath] = files[fpath].replace('break', 'break' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH1163_mlflow_21808',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'mlflow/mlflow',
                "pr_number": 21808,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/mlflow/mlflow/pull/21808",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'tests/server/jobs/test_endpoint.py': 'import os\nimport signal\nimport subprocess\nimport sys\nimport time\nfrom typing import Any\n\nimport pytest\nimport requests\n\nimport mlflow\nfrom mlflow.server.jobs import job\n\npytestmark = pytest.mark.skipif(\n    os.name == "nt", reason="MLflow job execution is not supported on Windows"\n)\n\n\n@job(name="simple_job_fun", max_workers=1)\ndef simple_job_fun(x: int, y: int, sleep_secs: int = 0) -> dict[str, Any]:\n    if sleep_secs:\n        time.sleep(sleep_secs)\n    return {\n        "a": x + y,\n        "b": x * y,\n    }\n\n\n@job(name="job_assert_tracking_uri", max_workers=1)\ndef job_assert_tracking_uri(server_url: str) -> None:\n    assert mlflow.get_tracking_uri() == server_url\n\n\nclass Client:\n    def __init__(self, server_url: str):\n        self.server_url = server_url\n\n    def submit_job(\n        self, job_name: str, params: dict[str, Any], timeout: float | None = None\n    ) -> dict[str, Any]:\n        payload = {\n            "job_name": job_name,\n            "params": params,\n            "timeout": timeout,\n        }\n        response = requests.post(f"{self.server_url}/ajax-api/3.0/jobs/", json=payload)\n        response.raise_for_status()\n        return response.json()\n\n    def post(self, path: str, payload: dict[str, Any]) -> requests.Response:\n        return requests.post(f"{self.server_url}{path}", json=payload)\n\n    def get_job(self, job_id: str) -> dict[str, Any]:\n        response = requests.get(f"{self.server_url}/ajax-api/3.0/jobs/{job_id}")\n        response.raise_for_status()\n        return response.json()\n\n    def cancel_job(self, job_id: str) -> dict[str, Any]:\n        response = requests.patch(f"{self.server_url}/ajax-api/3.0/jobs/cancel/{job_id}")\n        response.raise_for_status()\n        return response.json()\n\n    def wait_job(self, job_id: str, timeout: float = 10) -> dict[str, Any]:\n        beg_time = time.time()\n        while time.time() - beg_time <= timeout:\n            job_json = self.get_job(job_id)\n            if job_json["status"] in ["SUCCEEDED", "FAILED", "TIMEOUT"]:\n                return job_json\n            time.sleep(0.5)\n        raise TimeoutError("The job is not finalized within the timeout.")\n\n    def search_job(\n        self,\n        job_name: str | None = None,\n        params: dict[str, Any] | None = None,\n        statuses: list[str] | None = None,\n    ) -> list[dict[str, Any]]:\n        response = self.post(\n            "/ajax-api/3.0/jobs/search",\n            payload={\n                "job_name": job_name,\n                "params": params,\n                "statuses": statuses,\n            },\n        )\n        response.raise_for_status()\n        return response.json()["jobs"]\n\n\n@pytest.fixture(scope="module")\ndef client(tmp_path_factory: pytest.TempPathFactory) -> Client:\n    from tests.helper_functions import get_safe_port\n\n    tmp_path = tmp_path_factory.mktemp("server_mod")\n    backend_store_uri = f"sqlite:///{tmp_path / \'mlflow.db\'}"\n\n    port = get_safe_port()\n    with subprocess.Popen(\n        [\n            sys.executable,\n            "-m",\n            "mlflow",\n            "server",\n            "-h",\n            "127.0.0.1",\n            "-p",\n            str(port),\n            "--backend-store-uri",\n            backend_store_uri,\n        ],\n        env={\n            **os.environ,\n            "PYTHONPATH": os.path.dirname(__file__),\n            "MLFLOW_SERVER_ENABLE_JOB_EXECUTION": "true",\n            "_MLFLOW_SUPPORTED_JOB_FUNCTION_LIST": (\n                "test_endpoint.simple_job_fun,test_endpoint.job_assert_tracking_uri"\n            ),\n            "_MLFLOW_ALLOWED_JOB_NAME_LIST": ("simple_job_fun,job_assert_tracking_uri"),\n        },\n        start_new_session=True,  # new session & process group\n    ) as server_proc:\n        try:\n            time.sleep(10)  # wait the job runner up\n            # wait server up.\n            deadline = time.time() + 15\n            while time.time() < deadline:\n                time.sleep(1)\n                try:\n                    resp = requests.get(f"http://127.0.0.1:{port}/health")\n                except requests.ConnectionError:\n                    continue\n                if resp.status_code == 200:\n                    break\n            else:\n                raise TimeoutError("Server did not report healthy within 15 seconds")\n            yield Client(f"http://127.0.0.1:{port}")\n        finally:\n            # NOTE that we need to kill subprocesses\n            # (uvicorn server / huey task runner)\n            # so `killpg` is needed.\n            os.killpg(server_proc.pid, signal.SIGKILL)\n\n\ndef test_job_submit(client: Client):\n    job_id = client.submit_job(\n        job_name="simple_job_fun",\n        params={"x": 3, "y": 4},\n    )["job_id"]\n    job_json = client.wait_job(job_id, timeout=30)\n    job_json.pop("creation_time")\n    job_json.pop("last_update_time")\n    assert job_json == {\n        "job_id": job_id,\n        "job_name": "simple_job_fun",\n        "params": {"x": 3, "y": 4},\n        "timeout": None,\n        "status": "SUCCEEDED",\n        "result": {"a": 7, "b": 12},\n        "retry_count": 0,\n    }\n\n\ndef test_job_cancel(client: Client):\n    job_id = client.submit_job(\n        job_name="simple_job_fun",\n        params={"x": 3, "y": 4, "sleep_secs": 120},\n    )["job_id"]\n    time.sleep(2)\n\n    client.cancel_job(job_id)\n\n    job_json = client.get_job(job_id)\n    job_json.pop("creation_time")\n    job_json.pop("last_update_time")\n    assert job_json == {\n        "job_id": job_id,\n        "job_name": "simple_job_fun",\n        "params": {"x": 3, "y": 4, "sleep_secs": 120},\n        "timeout": None,\n        "status": "CANCELED",\n        "result": None,\n        "retry_count": 0,\n    }\n\n\ndef test_job_endpoint_invalid_job_name(client: Client):\n    payload = {\n        "job_name": "invalid_job_name",\n        "params": {"x": 3, "y": 4},\n    }\n    response = client.post("/ajax-api/3.0/jobs/", payload=payload)\n    assert response.status_code == 400\n    error_json = response.json()\n    assert "Invalid job name: invalid_job_name" in error_json["detail"]\n\n\ndef test_job_endpoint_missing_parameters(client: Client):\n    payload = {\n        "job_name": "simple_job_fun",\n        "params": {"x": 3},  # Missing required parameter \'y\'\n    }\n    response = client.post("/ajax-api/3.0/jobs/", payload=payload)\n\n    # Should return a 400 error with information about missing parameters\n    assert response.status_code == 400\n    assert response.json()["detail"] == (\n        "Missing required parameters for function \'simple_job_fun\': [\'y\']. "\n        + "Expected parameters: [\'x\', \'y\', \'sleep_secs\']"\n    )\n\n\ndef test_job_tracking_uri(client: Client):\n    job_id = client.submit_job(\n        job_name="job_assert_tracking_uri",\n        params={"server_url": client.server_url},\n    )["job_id"]\n    job_json = client.wait_job(job_id)\n    assert job_json["status"] == "SUCCEEDED"\n\n\ndef test_job_endpoint_search(client: Client):\n    job1_id = client.submit_job(\n        job_name="simple_job_fun",\n        params={"x": 7, "y": 4},\n    )["job_id"]\n\n    job2_id = client.submit_job(\n        job_name="simple_job_fun",\n        params={"x": 7, "y": 5},\n    )["job_id"]\n\n    job3_id = client.submit_job(\n        job_name="simple_job_fun",\n        params={"x": 4, "y": 5},\n    )["job_id"]\n\n    job4_id = client.submit_job(\n        job_name="simple_job_fun",\n        params={"x": 4, "y": 5, "sleep_secs": 5},\n        timeout=2,\n    )["job_id"]\n\n    client.wait_job(job1_id)\n    client.wait_job(job2_id)\n    client.wait_job(job3_id)\n    client.wait_job(job4_id)\n\n    def extract_job_ids(jobs: list[dict[str, Any]]) -> list[str]:\n        return [job_json["job_id"] for job_json in jobs]\n\n    jobs = client.search_job(\n        job_name="simple_job_fun",\n        params={"x": 7},\n    )\n    assert extract_job_ids(jobs) == [job1_id, job2_id]\n\n    jobs = client.search_job(\n        job_name="bad_fun_name",\n        params={"x": 7},\n    )\n    assert extract_job_ids(jobs) == []\n\n    jobs = client.search_job(\n        job_name="simple_job_fun",\n        params={"x": 7, "y": 5},\n    )\n    assert extract_job_ids(jobs) == [job2_id]\n\n    jobs = client.search_job(\n        job_name="simple_job_fun",\n        params={"y": 5},\n    )\n    assert extract_job_ids(jobs) == [job2_id, job3_id, job4_id]\n\n    jobs = client.search_job(\n        job_name="simple_job_fun",\n        params={"y": 6},\n    )\n    assert extract_job_ids(jobs) == []\n\n    jobs = client.search_job(\n        job_name="simple_job_fun",\n        params={"y": 5},\n        statuses=["SUCCEEDED"],\n    )\n    assert extract_job_ids(jobs) == [job2_id, job3_id]\n\n    jobs = client.search_job(\n        job_name="simple_job_fun",\n        params={"y": 5},\n        statuses=["TIMEOUT"],\n    )\n    assert extract_job_ids(jobs) == [job4_id]\n\n    jobs = client.search_job(\n        job_name="simple_job_fun",\n        params={"y": 5},\n        statuses=["SUCCEEDED", "TIMEOUT"],\n    )\n    assert extract_job_ids(jobs) == [job2_id, job3_id, job4_id]\n\n    response = client.post(\n        "/ajax-api/3.0/jobs/search",\n        payload={\n            "job_name": "simple_job_fun",\n            "statuses": ["BAD_STATUS"],\n        },\n    )\n    assert response.status_code == 422\n    assert (\n        response.json()["detail"][0]["msg"]\n        == "Input should be \'PENDING\', \'RUNNING\', \'SUCCEEDED\', \'FAILED\', \'TIMEOUT\' or \'CANCELED\'"\n    )\n',
        }
