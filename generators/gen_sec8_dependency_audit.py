"""
Parameterized generator for SEC8: Dependency Audit & Vulnerability Patch.

Each seed produces:
- A different application domain (data pipeline, web scraper, API client,
  report generator, notification service)
- Different pairs of vulnerable packages with real-looking CVE IDs
- Different "trap" package: latest version has a breaking API change
- Different safe version ranges and pinned versions
- Same structural fix pattern (bump to safe version, avoid breaking latest)

TNI Pattern B + C:
  Pattern B: Spec lists specific CVEs with package names and vulnerable version
             ranges. Brief is vague ("fix security vulnerabilities").
  Pattern C: One package's latest version is a plausible trap — it has a
             breaking API change documented in the spec. Agent must pick the
             correct safe version, not just `pip install --upgrade`.

Difficulty: expert
"""
from __future__ import annotations

from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom

# ---------------------------------------------------------------------------
# Variation pools
# ---------------------------------------------------------------------------

APP_DOMAINS = [
    {
        "name": "data_pipeline",
        "description": "ETL data-processing pipeline",
        "app_file": "pipeline.py",
        "extra_import": "import csv",
        "app_logic": """\
def run_pipeline(source_path: str) -> list[dict]:
    \"\"\"Read CSV, fetch remote data, and return merged records.\"\"\"
    records = []
    with open(source_path) as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            records.append(dict(row))
    return records
""",
        "test_func": "test_pipeline_runs",
        "test_body": """\
def test_pipeline_runs():
    import tempfile, os
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write("id,value\\n1,hello\\n")
        name = f.name
    try:
        result = run_pipeline(name)
        assert len(result) == 1
        assert result[0]["id"] == "1"
    finally:
        os.unlink(name)
""",
    },
    {
        "name": "web_scraper",
        "description": "HTTP web-scraping service",
        "app_file": "scraper.py",
        "extra_import": "import re",
        "app_logic": """\
def scrape_links(html: str) -> list[str]:
    \"\"\"Extract all href links from an HTML string.\"\"\"
    pattern = re.compile(r'href=[\\'\"]([^\\'\"]+)[\\'\"]')
    return pattern.findall(html)
""",
        "test_func": "test_scrape_links",
        "test_body": """\
def test_scrape_links():
    html = '<a href="https://example.com">link</a>'
    links = scrape_links(html)
    assert links == ["https://example.com"]
""",
    },
    {
        "name": "api_client",
        "description": "REST API client library",
        "app_file": "client.py",
        "extra_import": "import json",
        "app_logic": """\
def build_payload(data: dict) -> str:
    \"\"\"Serialize a dict to a JSON string for API submission.\"\"\"
    return json.dumps(data, sort_keys=True)
""",
        "test_func": "test_build_payload",
        "test_body": """\
def test_build_payload():
    payload = build_payload({"b": 2, "a": 1})
    import json
    parsed = json.loads(payload)
    assert parsed["a"] == 1 and parsed["b"] == 2
""",
    },
    {
        "name": "report_generator",
        "description": "Automated report generation service",
        "app_file": "reporter.py",
        "extra_import": "import datetime",
        "app_logic": """\
def generate_report(title: str, rows: list[dict]) -> dict:
    \"\"\"Generate a structured report dict with a timestamp.\"\"\"
    return {
        "title": title,
        "generated_at": datetime.datetime.utcnow().isoformat(),
        "row_count": len(rows),
        "rows": rows,
    }
""",
        "test_func": "test_generate_report",
        "test_body": """\
def test_generate_report():
    report = generate_report("Monthly", [{"id": 1}])
    assert report["title"] == "Monthly"
    assert report["row_count"] == 1
    assert "generated_at" in report
""",
    },
    {
        "name": "notification_service",
        "description": "Email/SMS notification dispatch service",
        "app_file": "notifier.py",
        "extra_import": "import hashlib",
        "app_logic": """\
def build_notification(recipient: str, message: str) -> dict:
    \"\"\"Build a notification envelope with a content hash for deduplication.\"\"\"
    digest = hashlib.sha256((recipient + message).encode()).hexdigest()
    return {"to": recipient, "body": message, "dedup_key": digest}
""",
        "test_func": "test_build_notification",
        "test_body": """\
def test_build_notification():
    n = build_notification("alice@example.com", "Hello")
    assert n["to"] == "alice@example.com"
    assert len(n["dedup_key"]) == 64  # sha256 hex
""",
    },
]

# ---------------------------------------------------------------------------
# Package variant pools
#
# Each entry describes two vulnerable packages and a third "trap" package.
# The trap package's latest version introduces a breaking API change.
#
# Fields:
#   pkg_a / pkg_b  — the two packages that must be patched
#   cve_a / cve_b  — CVE IDs for each
#   vuln_ver_a / vuln_ver_b  — vulnerable version pinned in requirements.txt
#   safe_ver_a / safe_ver_b  — the minimum safe version (what agent should use)
#   latest_ver_a / latest_ver_b — latest available version
#   pkg_trap              — package whose *latest* version is the trap
#   trap_safe_ver         — safe version to pin (NOT the latest)
#   trap_latest_ver       — breaking latest version
#   trap_breaking_change  — what breaks if you use trap_latest_ver
#   trap_api_old          — old API call used in the app
#   trap_api_new          — new API call in the latest (breaking) version
# ---------------------------------------------------------------------------

PKG_VARIANTS = [
    {
        "pkg_a": "requests",
        "cve_a": "CVE-2024-35195",
        "vuln_ver_a": "2.28.0",
        "safe_ver_a": "2.31.0",
        "latest_ver_a": "2.32.3",
        "severity_a": "HIGH",
        "desc_a": "Proxy-Authorization header leakage on redirect (SSRF enablement)",
        "pkg_b": "urllib3",
        "cve_b": "CVE-2024-37891",
        "vuln_ver_b": "1.26.14",
        "safe_ver_b": "1.26.19",
        "latest_ver_b": "2.2.2",
        "severity_b": "MEDIUM",
        "desc_b": "Cookie header forwarding to third-party hosts on redirect",
        # trap: cryptography — latest 42.x changes low-level key serialization API
        "pkg_trap": "cryptography",
        "trap_vuln_ver": "41.0.0",
        "trap_cve": "CVE-2024-26130",
        "trap_severity": "HIGH",
        "trap_desc": "NULL pointer dereference in PKCS12 parsing leading to DoS",
        "trap_safe_ver": "41.0.7",
        "trap_latest_ver": "42.0.8",
        "trap_breaking_change": (
            "cryptography 42.x removes the deprecated `default_backend()` "
            "import path. Code calling `from cryptography.hazmat.backends "
            "import default_backend` raises ImportError on 42.x."
        ),
        "trap_api_old": "from cryptography.hazmat.backends import default_backend",
        "trap_api_new": "# default_backend removed — use primitives directly",
        "app_uses_trap": True,
        "trap_import_line": "from cryptography.hazmat.backends import default_backend",
        "trap_usage_line": "    _backend = default_backend()  # required for key ops",
    },
    {
        "pkg_a": "pillow",
        "cve_a": "CVE-2024-28219",
        "vuln_ver_a": "9.4.0",
        "safe_ver_a": "10.3.0",
        "latest_ver_a": "10.4.0",
        "severity_a": "HIGH",
        "desc_a": "Buffer overflow in imagingutils C extension via crafted image",
        "pkg_b": "certifi",
        "cve_b": "CVE-2024-39689",
        "vuln_ver_b": "2023.7.22",
        "safe_ver_b": "2024.7.4",
        "latest_ver_b": "2024.8.30",
        "severity_b": "MEDIUM",
        "desc_b": "Compromised Entrust root CA certificate included in bundle",
        # trap: pyyaml — latest 6.0.2 changes the default Loader
        "pkg_trap": "pyyaml",
        "trap_vuln_ver": "5.3.1",
        "trap_cve": "CVE-2020-1747",
        "trap_severity": "CRITICAL",
        "trap_desc": "Arbitrary code execution via crafted YAML with python/object tag",
        "trap_safe_ver": "6.0.1",
        "trap_latest_ver": "6.0.2",
        "trap_breaking_change": (
            "PyYAML 6.0.2 enforces strict CLoader by default and removes "
            "the `yaml.load(data)` single-argument form. Code calling "
            "`yaml.load(data)` without an explicit Loader= raises TypeError on 6.0.2."
        ),
        "trap_api_old": "yaml.load(data)",
        "trap_api_new": "yaml.safe_load(data)  # or yaml.load(data, Loader=yaml.SafeLoader)",
        "app_uses_trap": True,
        "trap_import_line": "import yaml",
        "trap_usage_line": "    config = yaml.load(open('config.yaml'))  # load app config",
    },
    {
        "pkg_a": "jinja2",
        "cve_a": "CVE-2024-34064",
        "vuln_ver_a": "3.0.3",
        "safe_ver_a": "3.1.4",
        "latest_ver_a": "3.1.4",
        "severity_a": "MEDIUM",
        "desc_a": "XSS via xmlattr filter accepting keys with spaces in HTML context",
        "pkg_b": "werkzeug",
        "cve_b": "CVE-2024-34069",
        "vuln_ver_b": "2.3.6",
        "safe_ver_b": "3.0.3",
        "latest_ver_b": "3.0.6",
        "severity_b": "HIGH",
        "desc_b": "Remote code execution via debugger PIN brute-force",
        # trap: sqlalchemy — latest 2.x uses different declarative_base import
        "pkg_trap": "sqlalchemy",
        "trap_vuln_ver": "1.4.41",
        "trap_cve": "CVE-2023-23931",
        "trap_severity": "MEDIUM",
        "trap_desc": "Reflected SQL injection via improper quoting of bound parameters",
        "trap_safe_ver": "1.4.52",
        "trap_latest_ver": "2.0.31",
        "trap_breaking_change": (
            "SQLAlchemy 2.0 removes the legacy `declarative_base()` function "
            "from `sqlalchemy.ext.declarative`. Code using "
            "`from sqlalchemy.ext.declarative import declarative_base` "
            "raises ImportError on SQLAlchemy 2.x."
        ),
        "trap_api_old": "from sqlalchemy.ext.declarative import declarative_base",
        "trap_api_new": "from sqlalchemy.orm import DeclarativeBase  # SQLAlchemy 2.x",
        "app_uses_trap": True,
        "trap_import_line": "from sqlalchemy.ext.declarative import declarative_base",
        "trap_usage_line": "    Base = declarative_base()  # ORM base class",
    },
    {
        "pkg_a": "paramiko",
        "cve_a": "CVE-2023-48795",
        "vuln_ver_a": "2.12.0",
        "safe_ver_a": "3.4.0",
        "latest_ver_a": "3.4.1",
        "severity_a": "MEDIUM",
        "desc_a": "Terrapin prefix truncation attack on SSH handshake (RFC 9409)",
        "pkg_b": "pyopenssl",
        "cve_b": "CVE-2023-49083",
        "vuln_ver_b": "23.2.0",
        "safe_ver_b": "23.3.0",
        "latest_ver_b": "24.2.1",
        "severity_b": "MEDIUM",
        "desc_b": "NULL pointer dereference in PKCS12 decoding causes crash",
        # trap: boto3 — latest changes S3 client pagination API
        "pkg_trap": "boto3",
        "trap_vuln_ver": "1.26.0",
        "trap_cve": "CVE-2024-28180",
        "trap_severity": "HIGH",
        "trap_desc": "SSRF via crafted presigned URL in S3 client without endpoint validation",
        "trap_safe_ver": "1.34.0",
        "trap_latest_ver": "1.35.0",
        "trap_breaking_change": (
            "boto3 1.35.x changes the S3 `list_objects` response: the "
            "`Contents` key is now absent (not an empty list) when the bucket "
            "is empty. Code doing `response['Contents']` without a `.get()` "
            "guard raises KeyError on 1.35.x."
        ),
        "trap_api_old": "objects = response['Contents']",
        "trap_api_new": "objects = response.get('Contents', [])",
        "app_uses_trap": True,
        "trap_import_line": "import boto3",
        "trap_usage_line": "    s3 = boto3.client('s3')",
    },
    {
        "pkg_a": "aiohttp",
        "cve_a": "CVE-2024-23334",
        "vuln_ver_a": "3.8.6",
        "safe_ver_a": "3.9.2",
        "latest_ver_a": "3.10.5",
        "severity_a": "HIGH",
        "desc_a": "Path traversal in static file serving via symlink resolution",
        "pkg_b": "httpx",
        "cve_b": "CVE-2024-35195",
        "vuln_ver_b": "0.24.1",
        "safe_ver_b": "0.27.0",
        "latest_ver_b": "0.27.2",
        "severity_b": "MEDIUM",
        "desc_b": "Proxy-Authorization header not stripped on cross-origin redirect",
        # trap: pydantic — v2 breaks v1 models
        "pkg_trap": "pydantic",
        "trap_vuln_ver": "1.10.9",
        "trap_cve": "CVE-2024-3772",
        "trap_severity": "MEDIUM",
        "trap_desc": "Regular expression DoS in email validator via crafted email string",
        "trap_safe_ver": "1.10.21",
        "trap_latest_ver": "2.8.2",
        "trap_breaking_change": (
            "Pydantic v2 is a complete rewrite with a breaking API. Models "
            "defined with `class MyModel(BaseModel): field = validator(...)` "
            "using the v1 `@validator` decorator raise `PydanticUserError` on "
            "pydantic 2.x. Pin to 1.10.x to avoid the breaking change."
        ),
        "trap_api_old": "@validator('email')",
        "trap_api_new": "@field_validator('email')  # pydantic v2 API",
        "app_uses_trap": True,
        "trap_import_line": "from pydantic import BaseModel, validator",
        "trap_usage_line": "    @validator('email')\n    def validate_email(cls, v): return v",
    },
]


class Generator(TaskGenerator):
    task_id = "SEC8_dependency_audit"
    domain = "security"
    difficulty = "expert"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)

        domain = APP_DOMAINS[rng.randint(0, len(APP_DOMAINS) - 1)]
        pkg = PKG_VARIANTS[rng.randint(0, len(PKG_VARIANTS) - 1)]

        # Determine which package is the "trap" (the one where latest breaks)
        # The trap is always pkg_trap from the variant.
        trap_pkg = pkg["pkg_trap"]

        expected = {
            "domain": domain["name"],
            "pkg_a": pkg["pkg_a"],
            "cve_a": pkg["cve_a"],
            "safe_ver_a": pkg["safe_ver_a"],
            "pkg_b": pkg["pkg_b"],
            "cve_b": pkg["cve_b"],
            "safe_ver_b": pkg["safe_ver_b"],
            "trap_pkg": trap_pkg,
            "trap_cve": pkg["trap_cve"],
            "trap_safe_ver": pkg["trap_safe_ver"],
            "trap_latest_ver": pkg["trap_latest_ver"],
            "trap_must_not_use_latest": True,
            "fixes_required": [
                f"{pkg['pkg_a']}>={pkg['safe_ver_a']}",
                f"{pkg['pkg_b']}>={pkg['safe_ver_b']}",
                f"{trap_pkg}>={pkg['trap_safe_ver']},<{pkg['trap_latest_ver']}",
            ],
            "breaking_change_avoided": pkg["trap_breaking_change"],
        }

        workspace_files = {
            "requirements.txt": self._gen_requirements(pkg),
            domain["app_file"]: self._gen_app(domain, pkg),
            "tests/__init__.py": "",
            "tests/test_app.py": self._gen_tests(domain, pkg),
        }

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=self._gen_spec(domain, pkg),
            brief_md=self._gen_brief(domain),
            expected=expected,
            workspace_files=workspace_files,
        )

    # -------------------------------------------------------------------------
    # Workspace file generators
    # -------------------------------------------------------------------------

    def _gen_requirements(self, pkg: dict) -> str:
        lines = [
            f"{pkg['pkg_a']}=={pkg['vuln_ver_a']}",
            f"{pkg['pkg_b']}=={pkg['vuln_ver_b']}",
            f"{pkg['pkg_trap']}=={pkg['trap_vuln_ver']}",
        ]
        return "\n".join(lines) + "\n"

    def _gen_app(self, domain: dict, pkg: dict) -> str:
        trap_import = pkg["trap_import_line"]
        trap_usage = pkg["trap_usage_line"]
        app_logic = domain["app_logic"]
        extra_import = domain["extra_import"]

        return f'''\
"""
{domain["description"].capitalize()} application module.

Dependencies (see requirements.txt):
  - {pkg["pkg_a"]}
  - {pkg["pkg_b"]}
  - {pkg["pkg_trap"]}
"""
{extra_import}
{trap_import}


def _init_crypto():
    \"\"\"Initialize cryptographic backend (called at module load).\"\"\"
{trap_usage}


{app_logic}

if __name__ == "__main__":
    _init_crypto()
'''

    def _gen_tests(self, domain: dict, pkg: dict) -> str:
        test_func = domain["test_func"]
        test_body = domain["test_body"]
        app_file_no_ext = domain["app_file"].replace(".py", "")

        return f'''\
"""Tests for {domain["name"]} — must pass after dependency patches."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from {app_file_no_ext} import *


{test_body}

def test_requirements_patched():
    \"\"\"Verify that vulnerable packages are no longer present at vuln versions.\"\"\"
    import importlib.metadata as meta
    from packaging.version import Version

    # {pkg["pkg_a"]} must be >= {pkg["safe_ver_a"]}
    ver_a = Version(meta.version("{pkg["pkg_a"]}"))
    assert ver_a >= Version("{pkg["safe_ver_a"]}"), (
        f"{pkg["pkg_a"]} {{ver_a}} is still vulnerable (need >= {pkg["safe_ver_a"]})"
    )

    # {pkg["pkg_b"]} must be >= {pkg["safe_ver_b"]}
    ver_b = Version(meta.version("{pkg["pkg_b"]}"))
    assert ver_b >= Version("{pkg["safe_ver_b"]}"), (
        f"{pkg["pkg_b"]} {{ver_b}} is still vulnerable (need >= {pkg["safe_ver_b"]})"
    )

    # {pkg["pkg_trap"]} must be >= {pkg["trap_safe_ver"]} but < {pkg["trap_latest_ver"]}
    ver_trap = Version(meta.version("{pkg["pkg_trap"]}"))
    assert ver_trap >= Version("{pkg["trap_safe_ver"]}"), (
        f"{pkg["pkg_trap"]} {{ver_trap}} is still vulnerable (need >= {pkg["trap_safe_ver"]})"
    )
    assert ver_trap < Version("{pkg["trap_latest_ver"]}"), (
        f"{pkg["pkg_trap"]} {{ver_trap}} is the breaking latest version; "
        f"pin below {pkg["trap_latest_ver"]} to avoid API breakage"
    )
'''

    # -------------------------------------------------------------------------
    # Spec / brief generators
    # -------------------------------------------------------------------------

    def _gen_spec(self, domain: dict, pkg: dict) -> str:
        return f"""\
# SEC8: Dependency Audit — Vulnerability Patch Specification

## Overview

A security audit of the **{domain["description"]}** identified three CVEs in
pinned dependencies. You must patch all three to safe versions while preserving
application compatibility.

> **IMPORTANT — Read Before Patching**: One of the three packages has a
> "latest" release that introduces a **breaking API change** incompatible with
> the existing application code. Blindly running `pip install --upgrade` will
> break the app. The safe version range for each package is specified below.

---

## CVE Findings

### Finding 1 — {pkg["cve_a"]} ({pkg["severity_a"]})

| Field        | Value |
|---|---|
| **Package**  | `{pkg["pkg_a"]}` |
| **CVE**      | `{pkg["cve_a"]}` |
| **Severity** | {pkg["severity_a"]} |
| **Vulnerable versions** | `< {pkg["safe_ver_a"]}` |
| **Safe version range**  | `>= {pkg["safe_ver_a"]}` |
| **Current pinned version** | `{pkg["vuln_ver_a"]}` (VULNERABLE) |

**Description**: {pkg["desc_a"]}

**Required fix**: Upgrade `{pkg["pkg_a"]}` to `>= {pkg["safe_ver_a"]}` in
`requirements.txt`. The current pin of `{pkg["vuln_ver_a"]}` is vulnerable.
The latest release `{pkg["latest_ver_a"]}` is compatible and safe to use.

---

### Finding 2 — {pkg["cve_b"]} ({pkg["severity_b"]})

| Field        | Value |
|---|---|
| **Package**  | `{pkg["pkg_b"]}` |
| **CVE**      | `{pkg["cve_b"]}` |
| **Severity** | {pkg["severity_b"]} |
| **Vulnerable versions** | `< {pkg["safe_ver_b"]}` |
| **Safe version range**  | `>= {pkg["safe_ver_b"]}` |
| **Current pinned version** | `{pkg["vuln_ver_b"]}` (VULNERABLE) |

**Description**: {pkg["desc_b"]}

**Required fix**: Upgrade `{pkg["pkg_b"]}` to `>= {pkg["safe_ver_b"]}` in
`requirements.txt`. The current pin of `{pkg["vuln_ver_b"]}` is vulnerable.
The latest release `{pkg["latest_ver_b"]}` is compatible and safe to use.

---

### Finding 3 — {pkg["trap_cve"]} ({pkg["trap_severity"]}) ⚠ BREAKING CHANGE TRAP

| Field        | Value |
|---|---|
| **Package**  | `{pkg["pkg_trap"]}` |
| **CVE**      | `{pkg["trap_cve"]}` |
| **Severity** | {pkg["trap_severity"]} |
| **Vulnerable versions** | `< {pkg["trap_safe_ver"]}` |
| **Safe version range**  | `>= {pkg["trap_safe_ver"]}, < {pkg["trap_latest_ver"]}` |
| **Current pinned version** | `{pkg["trap_vuln_ver"]}` (VULNERABLE) |
| **Latest available**    | `{pkg["trap_latest_ver"]}` (**DO NOT USE — breaking change**) |

**Description**: {pkg["trap_desc"]}

**⚠ Breaking change in `{pkg["trap_latest_ver"]}`**: {pkg["trap_breaking_change"]}

**Required fix**: Upgrade `{pkg["pkg_trap"]}` to `>= {pkg["trap_safe_ver"]}` but
**pin it below `{pkg["trap_latest_ver"]}`** (i.e., use a specifier such as
`{pkg["pkg_trap"]}>={pkg["trap_safe_ver"]},<{pkg["trap_latest_ver"]}`). The
existing application code uses the old API (`{pkg["trap_api_old"]}`) which is
incompatible with `{pkg["trap_latest_ver"]}`. Do **not** upgrade to
`{pkg["trap_latest_ver"]}` without also updating the application code, and that
is explicitly **out of scope** for this task.

---

## Fix Requirements Summary

| # | Package | CVE | Current | Required range | Breaking trap? |
|---|---------|-----|---------|----------------|----------------|
| 1 | `{pkg["pkg_a"]}` | {pkg["cve_a"]} | `{pkg["vuln_ver_a"]}` | `>= {pkg["safe_ver_a"]}` | No |
| 2 | `{pkg["pkg_b"]}` | {pkg["cve_b"]} | `{pkg["vuln_ver_b"]}` | `>= {pkg["safe_ver_b"]}` | No |
| 3 | `{pkg["pkg_trap"]}` | {pkg["trap_cve"]} | `{pkg["trap_vuln_ver"]}` | `>= {pkg["trap_safe_ver"]}, < {pkg["trap_latest_ver"]}` | **YES** |

## Workspace Contents

- `requirements.txt` — pinned dependencies with vulnerable versions (patch this)
- `{domain["app_file"]}` — application module using all three packages
- `tests/test_app.py` — test suite (must pass after patching)

## Deliverables

The Executor must:
1. Update `requirements.txt` to eliminate all three CVEs using the safe version
   ranges above.
2. Ensure `{pkg["pkg_trap"]}` is pinned **below** `{pkg["trap_latest_ver"]}` to
   avoid the breaking API change.
3. Ensure the existing test suite (`tests/test_app.py`) continues to pass.
4. **Do not** modify any application source files (`{domain["app_file"]}`).

The Verifier must confirm:
- No vulnerable version pins remain for any of the three packages.
- `{pkg["pkg_trap"]}` is not upgraded to `{pkg["trap_latest_ver"]}`.
- The test suite passes without modification.
- `requirements.txt` is syntactically valid.
"""

    def _gen_brief(self, domain: dict) -> str:
        return f"""\
# SEC8: Dependency Audit (Executor Brief)

The **{domain["description"]}** has known security vulnerabilities in its
third-party dependencies. Fix them.

**Your workspace contains**:
- `requirements.txt` — dependency pins (some are vulnerable — patch these)
- Application source files — **do not modify**
- `tests/` — test suite that must continue to pass

The Planner has the full security audit report with CVE details and safe
version ranges. Read it carefully before patching — at least one package has
a latest release that will break the application.
"""
