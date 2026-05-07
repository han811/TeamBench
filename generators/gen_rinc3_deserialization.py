"""
Parameterized generator for RINC3: Unsafe Deserialization (RCE).

Inspiration: Multiple CVEs involving Python pickle (arbitrary code execution),
PyYAML yaml.load() (CVE-2017-18342), and eval() on untrusted input.
Workspace has a service that accepts serialized data from user input.

Seeds vary: deserialization vector (pickle/yaml/eval), service type,
endpoint name, and the RCE payload shape.

Grading: 7 checks — unsafe deserializer replaced, safe alternative used,
normal deserialization still works, RCE payload rejected.
"""
from __future__ import annotations

from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom

VARIANTS = [
    {
        "vector": "pickle",
        "service": "TaskQueueService",
        "endpoint": "/submit",
        "format": "pickle",
        "unsafe_call": "pickle.loads(data)",
        "safe_call": "json.loads(data.decode()) if isinstance(data, bytes) else json.loads(data)",
        "safe_import": "import json",
        "attack_desc": "arbitrary Python object deserialization — any class with __reduce__ can execute code",
        "fix_desc": "replace pickle.loads() with json.loads() for untrusted input",
        "content_type": "application/octet-stream",
        "param": "payload",
    },
    {
        "vector": "yaml_load",
        "service": "ConfigLoaderService",
        "endpoint": "/load-config",
        "format": "yaml",
        "unsafe_call": "yaml.load(data, Loader=yaml.Loader)",
        "safe_call": "yaml.safe_load(data)",
        "safe_import": "import yaml",
        "attack_desc": "yaml.load() with full Loader allows !!python/object tags that execute arbitrary code",
        "fix_desc": "replace yaml.load(..., Loader=yaml.Loader) with yaml.safe_load()",
        "content_type": "application/yaml",
        "param": "config",
    },
    {
        "vector": "eval",
        "service": "ExpressionEvalService",
        "endpoint": "/evaluate",
        "format": "expression",
        "unsafe_call": "eval(expression)",
        "safe_call": "ast.literal_eval(expression)",
        "safe_import": "import ast",
        "attack_desc": "eval() executes arbitrary Python — attacker can read files, run subprocesses, etc.",
        "fix_desc": "replace eval() with ast.literal_eval() for untrusted expressions",
        "content_type": "text/plain",
        "param": "expr",
    },
]


class Generator(TaskGenerator):
    task_id = "RINC3_deserialization"
    domain = "security"
    difficulty = "hard"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        v = VARIANTS[seed % len(VARIANTS)]
        port = rng.randint(5200, 5299)

        workspace_files = {
            "app.py": self._gen_app(v, port),
            "test_deser.py": self._gen_tests(v),
            "requirements.txt": self._gen_requirements(v),
        }

        expected = {
            "seed": seed,
            "vector": v["vector"],
            "service": v["service"],
            "unsafe_call": v["unsafe_call"],
            "fix": v["fix_desc"],
            "endpoint": v["endpoint"],
        }

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=self._gen_spec(v),
            brief_md=self._gen_brief(v),
            expected=expected,
            workspace_files=workspace_files,
            metadata={"difficulty": "hard", "category": "security", "cve_class": "OWASP-A08-2021"},
        )

    def _gen_requirements(self, v: dict) -> str:
        base = "flask>=2.3\npytest>=7.0\n"
        if v["vector"] == "yaml_load":
            base += "pyyaml>=6.0\n"
        return base

    def _gen_app(self, v: dict, port: int) -> str:
        if v["vector"] == "pickle":
            return self._gen_pickle_app(v, port)
        elif v["vector"] == "yaml_load":
            return self._gen_yaml_app(v, port)
        else:
            return self._gen_eval_app(v, port)

    def _gen_pickle_app(self, v: dict, port: int) -> str:
        return f'''\
"""
{v["service"]}: Accepts serialized task objects from clients.

WARNING: This code contains an unsafe deserialization vulnerability.
Inspiration: Python pickle RCE — any class with __reduce__ executes on load.
"""
import pickle
import base64
from flask import Flask, request, jsonify

app = Flask(__name__)


def process_task(task_data: dict) -> dict:
    """Process a deserialized task object."""
    return {{"status": "processed", "task_type": task_data.get("type", "unknown")}}


@app.route("{v["endpoint"]}", methods=["POST"])
def submit_task():
    """Accept a base64-encoded pickled task object.

    VULNERABLE: deserializes untrusted pickle data — RCE possible via __reduce__.
    """
    data = request.get_json()
    if not data or "{v["param"]}" not in data:
        return jsonify({{"error": "missing {v["param"]}"}}), 400

    try:
        raw = base64.b64decode(data["{v["param"]}"])
        # VULNERABILITY: pickle.loads on untrusted data allows arbitrary code execution
        task = pickle.loads(raw)
        result = process_task(task)
        return jsonify(result)
    except Exception as e:
        return jsonify({{"error": str(e)}}), 400


@app.route("/health")
def health():
    return jsonify({{"status": "ok", "service": "{v["service"]}"}})


if __name__ == "__main__":
    app.run(port={port}, debug=False)
'''

    def _gen_yaml_app(self, v: dict, port: int) -> str:
        return f'''\
"""
{v["service"]}: Loads user-provided YAML configuration.

WARNING: This code contains an unsafe deserialization vulnerability.
Inspiration: PyYAML yaml.load() RCE — CVE-2017-18342.
"""
import yaml
from flask import Flask, request, jsonify

app = Flask(__name__)


@app.route("{v["endpoint"]}", methods=["POST"])
def load_config():
    """Accept a YAML configuration string and parse it.

    VULNERABLE: yaml.load() with full Loader supports !!python/object tags,
    which can instantiate arbitrary Python objects and execute code.
    """
    data = request.get_json()
    if not data or "{v["param"]}" not in data:
        return jsonify({{"error": "missing {v["param"]}"}}), 400

    try:
        # VULNERABILITY: yaml.Loader supports !!python/object/apply: os.system
        config = yaml.load(data["{v["param"]}"], Loader=yaml.Loader)
        if not isinstance(config, dict):
            return jsonify({{"error": "config must be a YAML mapping"}}), 400
        # Only return safe keys
        safe_keys = ["name", "version", "debug", "timeout", "max_retries"]
        result = {{k: v for k, v in config.items() if k in safe_keys}}
        return jsonify({{"loaded": result}})
    except yaml.YAMLError as e:
        return jsonify({{"error": f"YAML parse error: {{e}}"}}), 400


@app.route("/health")
def health():
    return jsonify({{"status": "ok", "service": "{v["service"]}"}})


if __name__ == "__main__":
    app.run(port={port}, debug=False)
'''

    def _gen_eval_app(self, v: dict, port: int) -> str:
        return f'''\
"""
{v["service"]}: Evaluates user-provided Python literal expressions.

WARNING: This code contains a code injection vulnerability.
Inspiration: eval() on untrusted input — a classic RCE vector.
"""
from flask import Flask, request, jsonify

app = Flask(__name__)


@app.route("{v["endpoint"]}", methods=["POST"])
def evaluate_expression():
    """Evaluate a Python expression (intended for literals like lists/dicts).

    VULNERABLE: eval() executes arbitrary Python code, not just literals.
    An attacker can call __import__('os').system('...') etc.
    """
    data = request.get_json()
    if not data or "{v["param"]}" not in data:
        return jsonify({{"error": "missing {v["param"]}"}}), 400

    expression = data["{v["param"]}"]
    try:
        # VULNERABILITY: eval() executes arbitrary code
        result = eval(expression)
        return jsonify({{"result": repr(result), "type": type(result).__name__}})
    except Exception as e:
        return jsonify({{"error": str(e)}}), 400


@app.route("/health")
def health():
    return jsonify({{"status": "ok", "service": "{v["service"]}"}})


if __name__ == "__main__":
    app.run(port={port}, debug=False)
'''

    def _gen_tests(self, v: dict) -> str:
        if v["vector"] == "pickle":
            return self._gen_pickle_tests(v)
        elif v["vector"] == "yaml_load":
            return self._gen_yaml_tests(v)
        else:
            return self._gen_eval_tests(v)

    def _gen_pickle_tests(self, v: dict) -> str:
        return f'''\
"""Security tests for {v["service"]} — pickle deserialization."""
import base64
import json
import pickle
import pytest
import app as app_module


@pytest.fixture
def client():
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as c:
        yield c


def _encode(obj) -> str:
    return base64.b64encode(pickle.dumps(obj)).decode()


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200


def test_rce_payload_rejected(client):
    """A malicious pickle payload must be rejected (not executed)."""
    import os

    class RCEPayload:
        def __reduce__(self):
            # Would execute: touch /tmp/pwned
            return (os.system, ("touch /tmp/pwned_rinc3",))

    payload = base64.b64encode(pickle.dumps(RCEPayload())).decode()
    resp = client.post(
        "{v["endpoint"]}",
        json={{"{v["param"]}": payload}},
        content_type="application/json",
    )
    # Should be rejected — either 400 or the endpoint no longer uses pickle
    import os as _os
    assert not _os.path.exists("/tmp/pwned_rinc3"), (
        "RCE payload executed — /tmp/pwned_rinc3 was created"
    )


def test_safe_deserialization_works(client):
    """Normal JSON task data should be accepted after the fix."""
    import json, base64
    # After fix, endpoint should accept JSON-encoded data
    payload = base64.b64encode(json.dumps({{"type": "compute", "value": 42}}).encode()).decode()
    resp = client.post(
        "{v["endpoint"]}",
        json={{"{v["param"]}": payload}},
        content_type="application/json",
    )
    # Should not crash (200 or 400 with meaningful error, not 500)
    assert resp.status_code in (200, 400)


def test_no_pickle_loads_in_app(tmp_path):
    """Static check: app.py must not call pickle.loads() on request data."""
    import re, ast
    src = open("app.py").read()
    # Check for pickle.loads in the route handler
    assert "pickle.loads" not in src, (
        "app.py still contains pickle.loads() — replace with safe deserialization"
    )


def test_missing_payload_returns_400(client):
    resp = client.post("{v["endpoint"]}", json={{}}, content_type="application/json")
    assert resp.status_code == 400
'''

    def _gen_yaml_tests(self, v: dict) -> str:
        return f'''\
"""Security tests for {v["service"]} — yaml.load() deserialization."""
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


def test_rce_yaml_payload_rejected(client):
    """A !!python/object YAML payload must not execute code."""
    import os
    malicious_yaml = "!!python/object/apply:os.system ['touch /tmp/pwned_rinc3']"
    resp = client.post(
        "{v["endpoint"]}",
        json={{"{v["param"]}": malicious_yaml}},
        content_type="application/json",
    )
    import os as _os
    assert not _os.path.exists("/tmp/pwned_rinc3"), (
        "RCE payload executed — /tmp/pwned_rinc3 was created"
    )


def test_safe_yaml_works(client):
    """Normal YAML config should load correctly."""
    safe_yaml = "name: myapp\\nversion: 1\\ntimeout: 30"
    resp = client.post(
        "{v["endpoint"]}",
        json={{"{v["param"]}": safe_yaml}},
        content_type="application/json",
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert "loaded" in data
    assert data["loaded"].get("name") == "myapp"


def test_no_yaml_loader_in_app():
    """Static check: app.py must not use yaml.Loader (full loader)."""
    src = open("app.py").read()
    assert "yaml.Loader" not in src, (
        "app.py still uses yaml.Loader — replace with yaml.safe_load()"
    )


def test_yaml_object_tag_rejected(client):
    """YAML !!python/object tag must be rejected."""
    evil = "!!python/object:os.path.join []"
    resp = client.post(
        "{v["endpoint"]}",
        json={{"{v["param"]}": evil}},
        content_type="application/json",
    )
    assert resp.status_code in (400, 500), (
        f"YAML object tag not rejected: status={{resp.status_code}}"
    )
'''

    def _gen_eval_tests(self, v: dict) -> str:
        return f'''\
"""Security tests for {v["service"]} — eval() injection."""
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
        "{v["endpoint"]}",
        json={{"{v["param"]}": payload}},
        content_type="application/json",
    )
    import os as _os
    assert not _os.path.exists("/tmp/pwned_rinc3"), (
        "RCE payload executed — /tmp/pwned_rinc3 was created"
    )


def test_literal_list_works(client):
    """Literal list expression should evaluate correctly."""
    resp = client.post(
        "{v["endpoint"]}",
        json={{"{v["param"]}": "[1, 2, 3]"}},
        content_type="application/json",
    )
    assert resp.status_code == 200
    assert "result" in resp.get_json()


def test_literal_dict_works(client):
    """Literal dict expression should evaluate correctly."""
    resp = client.post(
        "{v["endpoint"]}",
        json={{"{v["param"]}": '{{"key": "value"}}'}},
        content_type="application/json",
    )
    assert resp.status_code == 200


def test_function_call_rejected(client):
    """Function calls must be rejected by ast.literal_eval."""
    resp = client.post(
        "{v["endpoint"]}",
        json={{"{v["param"]}": "print('hello')"}},
        content_type="application/json",
    )
    assert resp.status_code in (400, 500), (
        f"Function call not rejected: status={{resp.status_code}}"
    )


def test_no_bare_eval_in_app():
    """Static check: app.py must not contain bare eval() call."""
    import re
    src = open("app.py").read()
    # Should not have eval( without ast. prefix
    matches = re.findall(r'(?<!ast\.)(?<!literal_)eval\s*\(', src)
    assert not matches, (
        f"app.py still contains bare eval(): {{matches}}"
    )
'''

    def _gen_spec(self, v: dict) -> str:
        return f"""# RINC3: Unsafe Deserialization — {v["vector"].upper()}

## Incident Background
Inspired by multiple CVEs involving unsafe deserialization in Python applications.
The `{v["vector"]}` vector allows attackers to execute arbitrary code on the server
by sending a crafted payload to the `{v["endpoint"]}` endpoint.

## Service: {v["service"]}
File: `app.py`

## Vulnerability
**Location:** `{v["endpoint"]}` route handler in `app.py`
**Unsafe operation:** `{v["unsafe_call"]}`
**Attack:** {v["attack_desc"]}

**Concrete attack payload:**
```
POST {v["endpoint"]}
{v["param"]}=<malicious_{v["format"]}_payload>
```
A crafted payload causes the server to execute arbitrary OS commands.

## Required Fix
{v["fix_desc"]}

Replace:
```python
{v["unsafe_call"]}
```
With the safe alternative that only handles data types, not code execution.

## Acceptance Criteria
1. A malicious `{v["vector"]}` payload does NOT execute code (no /tmp/pwned file)
2. Normal `{v["format"]}` data continues to be processed correctly
3. The unsafe call `{v["unsafe_call"]}` no longer appears in `app.py`
4. Missing/malformed input returns 400
5. All tests pass: `pytest test_deser.py -v`

## Files
- `app.py` — fix the unsafe deserialization call
- `test_deser.py` — do NOT modify
"""

    def _gen_brief(self, v: dict) -> str:
        return f"""# RINC3: Unsafe Deserialization Fix (Brief)

The {v["service"]} is processing user-provided {v["format"]} data in a way
that could allow attackers to run arbitrary code on the server.

Fix the deserialization vulnerability in `app.py`.

Verify with:
```
pytest test_deser.py -v
```

**Files to fix:** `app.py`
**Do NOT modify:** `test_deser.py`
"""
