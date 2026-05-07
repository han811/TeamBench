"""
Path traversal security tests for StaticFileServer.
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
    resp = client.get("/serve?file=report_682.txt")
    assert resp.status_code == 200


def test_list_files(client):
    resp = client.get("/list")
    assert resp.status_code == 200
    assert "files" in resp.get_json()


def test_dot_dot_slash_blocked(client):
    """../../etc/passwd must be blocked."""
    resp = client.get("/serve?file=../../etc/passwd")
    assert resp.status_code in (400, 403, 404), (
        f"Path traversal ../../etc/passwd not blocked: status={resp.status_code}"
    )


def test_deep_traversal_blocked(client):
    """../../../../etc/shadow must be blocked."""
    resp = client.get("/serve?file=../../../../etc/shadow")
    assert resp.status_code in (400, 403, 404)


def test_absolute_path_blocked(client):
    """Absolute path /etc/passwd must be blocked."""
    resp = client.get("/serve?file=/etc/passwd")
    assert resp.status_code in (400, 403, 404), (
        f"Absolute path not blocked: status={resp.status_code}"
    )


def test_traversal_does_not_read_etc_passwd(client):
    """Verify traversal payload does not return /etc/passwd content."""
    resp = client.get("/serve?file=../../../etc/passwd")
    if resp.status_code == 200:
        content = resp.data.decode("utf-8", errors="replace")
        assert "root:" not in content, (
            "Path traversal succeeded — /etc/passwd content returned"
        )


def test_resolve_file_path_stays_in_base():
    """resolve_file_path() must raise or return path within BASE_DIR."""
    import os
    base = os.path.abspath("static")
    try:
        result = app_module.resolve_file_path("../../../../etc/passwd")
        assert result.startswith(base), (
            f"resolve_file_path escaped BASE_DIR: {result}"
        )
    except (ValueError, PermissionError):
        pass  # Raising is also acceptable
