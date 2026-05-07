"""Security tests for ExpressionEvalService — eval() injection."""
import pytest
import app as app_module


@pytest.fixture
def client():
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as c:
        yield c


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200


def test_rce_payload_rejected(client):
    """eval() on __import__('os').system must be blocked."""
    import os
    payload = "__import__('os').system('touch /tmp/pwned_rinc3')"
    resp = client.post(
        "/evaluate",
        json={"expr": payload},
        content_type="application/json",
    )
    import os as _os
    assert not _os.path.exists("/tmp/pwned_rinc3"), (
        "RCE payload executed — /tmp/pwned_rinc3 was created"
    )


def test_literal_list_works(client):
    """Literal list expression should evaluate correctly."""
    resp = client.post(
        "/evaluate",
        json={"expr": "[1, 2, 3]"},
        content_type="application/json",
    )
    assert resp.status_code == 200
    assert "result" in resp.get_json()


def test_literal_dict_works(client):
    """Literal dict expression should evaluate correctly."""
    resp = client.post(
        "/evaluate",
        json={"expr": '{"key": "value"}'},
        content_type="application/json",
    )
    assert resp.status_code == 200


def test_function_call_rejected(client):
    """Function calls must be rejected by ast.literal_eval."""
    resp = client.post(
        "/evaluate",
        json={"expr": "print('hello')"},
        content_type="application/json",
    )
    assert resp.status_code in (400, 500), (
        f"Function call not rejected: status={resp.status_code}"
    )


def test_no_bare_eval_in_app():
    """Static check: app.py must not contain bare eval() call."""
    import re
    src = open("app.py").read()
    # Should not have eval( without ast. prefix
    matches = re.findall(r'(?<!ast\.)(?<!literal_)eval\s*\(', src)
    assert not matches, (
        f"app.py still contains bare eval(): {matches}"
    )
