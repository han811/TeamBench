"""
Parameterized generator for RINC5: Path Traversal / Directory Traversal.

Inspiration: Numerous CVEs involving file download endpoints that don't
sanitize the filename parameter (e.g., ../../../../etc/passwd).
Workspace has a file server / download endpoint with unsanitized path.

Seeds vary: traversal technique (../seq / null byte / double encoding),
service name, base directory, file parameter name.

Grading: 7 checks — traversal blocked, legitimate downloads still work,
path sanitization in place, no access to files outside base dir.
"""
from __future__ import annotations

from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom

VARIANTS = [
    {
        "technique": "dot_dot_slash",
        "service": "FileDownloadService",
        "base_dir": "files",
        "param": "filename",
        "endpoint": "/download",
        "vuln_desc": "filename parameter not normalized — ../../../etc/passwd traverses out of base dir",
        "fix_desc": "use os.path.realpath() and verify the resolved path starts with the allowed base directory",
        "attack_payload": "../../../../etc/passwd",
    },
    {
        "technique": "double_encoding",
        "service": "StaticFileServer",
        "base_dir": "static",
        "param": "file",
        "endpoint": "/serve",
        "vuln_desc": "double URL encoding bypasses naive ../ filter: %252e%252e%252f decoded twice gives ../",
        "fix_desc": "normalize path with os.path.realpath() after URL decoding — do not rely on string-replace filters",
        "attack_payload": "%252e%252e%252fetc%252fpasswd",
    },
    {
        "technique": "null_byte",
        "service": "ReportExporter",
        "base_dir": "reports",
        "param": "report",
        "endpoint": "/export",
        "vuln_desc": "null byte injection terminates path string in C-based functions: report.pdf\\x00/../../../etc/passwd",
        "fix_desc": "reject filenames containing null bytes (\\x00) and normalize with os.path.realpath()",
        "attack_payload": "report.pdf\x00/../../../etc/passwd",
    },
]


class Generator(TaskGenerator):
    task_id = "RINC5_path_traversal"
    domain = "security"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        v = VARIANTS[seed % len(VARIANTS)]
        port = rng.randint(5400, 5499)
        sample_files = [f"report_{rng.randint(100,999)}.txt",
                        f"data_{rng.randint(100,999)}.csv",
                        f"export_{rng.randint(100,999)}.json"]

        workspace_files = {
            "app.py": self._gen_app(v, port, sample_files),
            "setup_files.py": self._gen_setup(v, sample_files),
            "test_traversal.py": self._gen_tests(v, sample_files),
            "requirements.txt": "flask>=2.3\npytest>=7.0\n",
        }

        expected = {
            "seed": seed,
            "technique": v["technique"],
            "service": v["service"],
            "base_dir": v["base_dir"],
            "fix": v["fix_desc"],
            "attack_payload": v["attack_payload"],
            "sample_files": sample_files,
        }

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=self._gen_spec(v, sample_files),
            brief_md=self._gen_brief(v),
            expected=expected,
            workspace_files=workspace_files,
            metadata={"difficulty": "medium", "category": "security", "cve_class": "CWE-22"},
        )

    def _gen_app(self, v: dict, port: int, sample_files: list) -> str:
        return f'''\
"""
{v["service"]}: Serves files from the '{v["base_dir"]}/' directory.

WARNING: This code contains a path traversal vulnerability.
Inspiration: CWE-22 Path Traversal — one of the most common file-serving bugs.
"""
import os
from flask import Flask, request, send_file, jsonify, abort

app = Flask(__name__)
BASE_DIR = os.path.abspath("{v["base_dir"]}")


def resolve_file_path(filename: str) -> str:
    """Resolve a filename to an absolute path within BASE_DIR.

    VULNERABLE: does not check that the resolved path stays within BASE_DIR.
    An attacker can use ../ sequences to escape the base directory.
    """
    # VULNERABILITY: os.path.join with an absolute path or ../ sequences
    # can escape BASE_DIR entirely
    path = os.path.join(BASE_DIR, filename)
    # NOTE: no realpath() normalization, no prefix check
    return path


@app.route("{v["endpoint"]}")
def download_file():
    """Download a file by name from the {v["base_dir"]}/ directory."""
    filename = request.args.get("{v["param"]}", "")
    if not filename:
        return jsonify({{"error": "missing {v["param"]} parameter"}}), 400

    try:
        file_path = resolve_file_path(filename)
        if not os.path.isfile(file_path):
            return jsonify({{"error": "file not found"}}), 404
        return send_file(file_path)
    except Exception as e:
        return jsonify({{"error": str(e)}}), 500


@app.route("/list")
def list_files():
    """List available files in the base directory."""
    if not os.path.isdir(BASE_DIR):
        return jsonify({{"files": []}})
    files = [f for f in os.listdir(BASE_DIR) if os.path.isfile(os.path.join(BASE_DIR, f))]
    return jsonify({{"files": files, "base_dir": "{v["base_dir"]}"}})


@app.route("/health")
def health():
    return jsonify({{"status": "ok", "service": "{v["service"]}"}})


if __name__ == "__main__":
    app.run(port={port}, debug=False)
'''

    def _gen_setup(self, v: dict, sample_files: list) -> str:
        base_dir = v["base_dir"]
        files_init = "\n".join(
            f'open(os.path.join(base, "{f}"), "w").write("sample content for {f}")' for f in sample_files
        )
        return f'''\
"""Create the {base_dir}/ directory with sample files."""
import os

base = "{base_dir}"
os.makedirs(base, exist_ok=True)
{files_init}
print(f"Created {{len(os.listdir(base))}} files in {{base}}/")
'''

    def _gen_tests(self, v: dict, sample_files: list) -> str:
        first_file = sample_files[0]
        return f'''\
"""
Path traversal security tests for {v["service"]}.
"""
import os
import pytest
import setup_files
setup_files  # ensure setup runs on import? No — run it explicitly.

import subprocess, sys
subprocess.run([sys.executable, "setup_files.py"], check=True)

import app as app_module


@pytest.fixture
def client():
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as c:
        yield c


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200


def test_legitimate_file_download(client):
    """A file inside the base directory must be downloadable."""
    resp = client.get("{v["endpoint"]}?{v["param"]}={first_file}")
    assert resp.status_code == 200


def test_list_files(client):
    resp = client.get("/list")
    assert resp.status_code == 200
    assert "files" in resp.get_json()


def test_dot_dot_slash_blocked(client):
    """../../etc/passwd must be blocked."""
    resp = client.get("{v["endpoint"]}?{v["param"]}=../../etc/passwd")
    assert resp.status_code in (400, 403, 404), (
        f"Path traversal ../../etc/passwd not blocked: status={{resp.status_code}}"
    )


def test_deep_traversal_blocked(client):
    """../../../../etc/shadow must be blocked."""
    resp = client.get("{v["endpoint"]}?{v["param"]}=../../../../etc/shadow")
    assert resp.status_code in (400, 403, 404)


def test_absolute_path_blocked(client):
    """Absolute path /etc/passwd must be blocked."""
    resp = client.get("{v["endpoint"]}?{v["param"]}=/etc/passwd")
    assert resp.status_code in (400, 403, 404), (
        f"Absolute path not blocked: status={{resp.status_code}}"
    )


def test_traversal_does_not_read_etc_passwd(client):
    """Verify traversal payload does not return /etc/passwd content."""
    resp = client.get("{v["endpoint"]}?{v["param"]}=../../../etc/passwd")
    if resp.status_code == 200:
        content = resp.data.decode("utf-8", errors="replace")
        assert "root:" not in content, (
            "Path traversal succeeded — /etc/passwd content returned"
        )


def test_resolve_file_path_stays_in_base():
    """resolve_file_path() must raise or return path within BASE_DIR."""
    import os
    base = os.path.abspath("{v["base_dir"]}")
    try:
        result = app_module.resolve_file_path("../../../../etc/passwd")
        assert result.startswith(base), (
            f"resolve_file_path escaped BASE_DIR: {{result}}"
        )
    except (ValueError, PermissionError):
        pass  # Raising is also acceptable
'''

    def _gen_spec(self, v: dict, sample_files: list) -> str:
        return f"""# RINC5: Path Traversal Vulnerability

## Incident Background
Inspired by CWE-22 (Path Traversal) — one of the most consistently exploited
vulnerability classes. File download endpoints that don't normalize paths allow
attackers to read arbitrary files on the server.

## Service: {v["service"]}
File: `app.py` | Base directory: `{v["base_dir"]}/`

## Vulnerability
**Technique:** {v["technique"]}
**Description:** {v["vuln_desc"]}

**Vulnerable function:**
```python
def resolve_file_path(filename: str) -> str:
    path = os.path.join(BASE_DIR, filename)
    # No realpath() normalization, no prefix check
    return path
```

**Attack:**
```
GET {v["endpoint"]}?{v["param"]}=../../../../etc/passwd
→ Returns contents of /etc/passwd
```

## Required Fix
{v["fix_desc"]}

```python
def resolve_file_path(filename: str) -> str:
    if '\\x00' in filename:          # reject null bytes
        raise ValueError("Invalid filename")
    path = os.path.realpath(os.path.join(BASE_DIR, filename))
    if not path.startswith(BASE_DIR + os.sep) and path != BASE_DIR:
        raise ValueError("Path traversal detected")
    return path
```

## Sample Files
Files available in `{v["base_dir"]}/`: {", ".join(f"`{f}`" for f in sample_files)}

## Acceptance Criteria
1. `{v["endpoint"]}?{v["param"]}=../../etc/passwd` → 400/403/404
2. `{v["endpoint"]}?{v["param"]}=../../../../etc/shadow` → 400/403/404
3. `{v["endpoint"]}?{v["param"]}=/etc/passwd` → 400/403/404
4. `{v["endpoint"]}?{v["param"]}={sample_files[0]}` → 200 (legitimate file works)
5. `resolve_file_path()` does not return paths outside `{v["base_dir"]}/`
6. All tests pass: `pytest test_traversal.py -v`

## Files
- `app.py` — fix `resolve_file_path()` function
- `setup_files.py` — do NOT modify
- `test_traversal.py` — do NOT modify
"""

    def _gen_brief(self, v: dict) -> str:
        return f"""# RINC5: Path Traversal Fix (Brief)

The {v["service"]}'s `{v["endpoint"]}` endpoint has been flagged — it may
allow access to files outside the intended `{v["base_dir"]}/` directory.

Fix the file path resolution in `app.py`.

Setup and verify with:
```
python setup_files.py
pytest test_traversal.py -v
```

**Files to fix:** `app.py`
**Do NOT modify:** `setup_files.py`, `test_traversal.py`
"""
