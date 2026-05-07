"""
Parameterized generator for RINC10: Config Drift — Production vs Version Control.

Inspiration: Multiple real incidents where production config diverged from
version-controlled config (Knight Capital, various cloud outages). Ops team
manually edited production config months ago; git shows a different state.
Monitoring alerts fire but engineers can't correlate which config values
are wrong.

Workspace has: git-committed config (correct) + deployed production config
(drifted) + monitoring data showing anomalies. Corpus includes deployment
logs hinting at when drift was introduced.

Seeds vary: service type (rate limiter / feature flags / DB pool),
number of drifted keys (3-5), types of drift (wrong value / extra key /
missing key).

Grading: 7 checks — drifted keys identified, config reconciled to match
VCS state, service starts with correct config, no regressions.
"""
from __future__ import annotations

import json

from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom

SERVICE_CONFIGS = [
    {
        "service": "RateLimiterService",
        "config_file": "config/rate_limiter.json",
        "vcs_config": {
            "requests_per_second": 100,
            "burst_size": 200,
            "retry_after_seconds": 60,
            "enable_throttling": True,
            "whitelist_ips": ["10.0.0.1", "10.0.0.2"],
            "log_level": "info",
            "timeout_ms": 500,
        },
        "drift_targets": ["requests_per_second", "burst_size", "retry_after_seconds"],
        "drift_values": [10, 20, 600],   # too low / too low / too long
        "drift_explanation": "rate limit set 10x too low after manual tuning for load test, never reverted",
        "monitoring_symptom": "429 error rate 45% — requests getting throttled unexpectedly",
    },
    {
        "service": "FeatureFlagService",
        "config_file": "config/feature_flags.json",
        "vcs_config": {
            "enable_new_checkout": True,
            "enable_recommendations": True,
            "enable_dark_mode": False,
            "ab_test_percentage": 50,
            "max_items_per_page": 25,
            "cache_ttl_seconds": 300,
            "enable_analytics": True,
        },
        "drift_targets": ["enable_new_checkout", "ab_test_percentage", "cache_ttl_seconds"],
        "drift_values": [False, 5, 30],  # feature off / tiny AB test / tiny cache
        "drift_explanation": "checkout feature disabled for hotfix, AB test % reduced for incident, never re-enabled",
        "monitoring_symptom": "checkout conversion 60% below normal — new checkout flow disabled in production",
    },
    {
        "service": "DatabasePoolService",
        "config_file": "config/db_pool.json",
        "vcs_config": {
            "max_connections": 50,
            "min_connections": 5,
            "connection_timeout_ms": 5000,
            "idle_timeout_seconds": 600,
            "max_lifetime_seconds": 3600,
            "enable_ssl": True,
            "ssl_mode": "verify-full",
        },
        "drift_targets": ["max_connections", "connection_timeout_ms", "enable_ssl"],
        "drift_values": [5, 500, False],  # pool too small / timeout too short / SSL off
        "drift_explanation": "max_connections reduced to debug pool exhaustion, SSL disabled to bypass cert issue, neither reverted",
        "monitoring_symptom": "connection pool exhaustion p99 latency 8s — max_connections too low, SSL disabled",
    },
]


class Generator(TaskGenerator):
    task_id = "RINC10_config_drift"
    domain = "incident"
    difficulty = "hard"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        svc = SERVICE_CONFIGS[seed % len(SERVICE_CONFIGS)]

        # Build production (drifted) config
        prod_config = dict(svc["vcs_config"])
        for key, val in zip(svc["drift_targets"], svc["drift_values"]):
            prod_config[key] = val

        # Add an extra key in production not in VCS (also drift)
        extra_key = rng.choice(["debug_mode", "temp_override", "manual_override"])
        prod_config[extra_key] = True

        workspace_files = {
            svc["config_file"]: json.dumps(prod_config, indent=2),  # drifted production config
            "config/vcs_config.json": json.dumps(svc["vcs_config"], indent=2),  # VCS reference (correct)
            "service.py": self._gen_service(svc),
            "reconcile.py": self._gen_reconcile_stub(svc),
            "test_config.py": self._gen_tests(svc, prod_config, extra_key),
            "requirements.txt": "pytest>=7.0\n",
        }

        corpus_files = {
            "deployment_log.txt": self._gen_deployment_log(svc, rng),
            "monitoring_alerts.json": self._gen_monitoring_alerts(svc, rng),
        }

        expected = {
            "seed": seed,
            "service": svc["service"],
            "drifted_keys": svc["drift_targets"] + [extra_key],
            "correct_config": svc["vcs_config"],
            "drift_explanation": svc["drift_explanation"],
            "extra_key": extra_key,
        }

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=self._gen_spec(svc, prod_config, extra_key),
            brief_md=self._gen_brief(svc),
            expected=expected,
            workspace_files=workspace_files,
            corpus_files=corpus_files,
            metadata={"difficulty": "hard", "category": "incident", "incident": "config-drift"},
        )

    def _gen_deployment_log(self, svc: dict, rng: SeededRandom) -> str:
        days_ago = rng.randint(14, 90)
        hour = rng.randint(1, 23)
        return f"""DEPLOYMENT LOG — {svc["service"]}
========================================

2026-01-{(28 - days_ago % 28):02d} {hour:02d}:34:12 UTC  [AUTOMATED] Deploy v2.14.3 — production
  Config hash: a3f7b9c1 (matches VCS)
  Status: SUCCESS

2026-01-{(28 - days_ago % 28 + 2) % 28 + 1:02d} 14:22:07 UTC  [MANUAL] Hotfix config edit — ops-engineer
  Reason: {svc["drift_explanation"].split(",")[0]}
  Changed: {svc["drift_targets"][0]} = {svc["drift_values"][0]}
  NOTE: "temporary, will revert after incident"
  Status: APPLIED_WITHOUT_COMMIT

2026-02-03 09:15:44 UTC  [MANUAL] Additional config edit — ops-engineer
  Reason: {svc["drift_explanation"].split(",")[1] if "," in svc["drift_explanation"] else "follow-up adjustment"}
  Changed: {svc["drift_targets"][1]} = {svc["drift_values"][1]}
  NOTE: "quick fix for load test"
  Status: APPLIED_WITHOUT_COMMIT

2026-02-15 16:48:22 UTC  [AUTOMATED] Deploy v2.15.0 — production
  Config hash: MISMATCH — production differs from VCS
  WARNING: Config drift detected but deploy continued
  Status: SUCCESS (config NOT updated from VCS)

2026-03-01 00:00:00 UTC  [MONITORING] Config drift alarm
  Alert: Production config diverges from git HEAD
  Drifted keys detected: {len(svc["drift_targets"]) + 1}
  Symptom: {svc["monitoring_symptom"]}
"""

    def _gen_monitoring_alerts(self, svc: dict, rng: SeededRandom) -> str:
        alerts = [
            {
                "timestamp": "2026-03-01T00:00:00Z",
                "severity": "critical",
                "service": svc["service"],
                "alert": "CONFIG_DRIFT_DETECTED",
                "message": svc["monitoring_symptom"],
                "details": {
                    "config_file": svc["config_file"],
                    "production_hash": "d8a3f1b2",
                    "vcs_hash": "a3f7b9c1",
                    "drifted_key_count": len(svc["drift_targets"]) + 1,
                }
            },
            {
                "timestamp": "2026-03-01T00:05:00Z",
                "severity": "warning",
                "service": svc["service"],
                "alert": "PERFORMANCE_DEGRADATION",
                "message": f"P99 latency increased 3x since config change",
                "details": {
                    "p99_before": "120ms",
                    "p99_after": "890ms",
                    "correlated_config_key": svc["drift_targets"][0],
                }
            }
        ]
        return json.dumps(alerts, indent=2)

    def _gen_service(self, svc: dict) -> str:
        config_file = svc["config_file"]
        service_name = svc["service"]
        return f'''\
"""
{service_name}: Loads and validates its configuration.

The service reads from {config_file}. Production config has drifted
from the VCS-controlled reference (config/vcs_config.json).
"""
import json
import os


CONFIG_FILE = "{config_file}"
VCS_CONFIG_FILE = "config/vcs_config.json"


def load_config(path: str = CONFIG_FILE) -> dict:
    """Load configuration from JSON file."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found: {{path}}")
    with open(path) as f:
        return json.load(f)


def validate_config(config: dict) -> list[str]:
    """Validate config keys and types. Returns list of error strings."""
    errors = []
    vcs = load_config(VCS_CONFIG_FILE)

    # Check for missing keys
    for key in vcs:
        if key not in config:
            errors.append(f"Missing key: {{key}}")

    # Check for extra keys not in VCS spec
    for key in config:
        if key not in vcs:
            errors.append(f"Extra key not in VCS spec: {{key}}")

    # Check types match
    for key in vcs:
        if key in config and type(config[key]) != type(vcs[key]):
            errors.append(f"Type mismatch for {{key}}: expected {{type(vcs[key]).__name__}}, got {{type(config[key]).__name__}}")

    return errors


def diff_configs(production: dict, vcs: dict) -> dict:
    """Compare production config to VCS config, return differences."""
    diffs = {{}}
    all_keys = set(production) | set(vcs)
    for key in all_keys:
        prod_val = production.get(key, "<MISSING>")
        vcs_val = vcs.get(key, "<MISSING>")
        if prod_val != vcs_val:
            diffs[key] = {{"production": prod_val, "vcs": vcs_val}}
    return diffs


def start_service(config: dict) -> dict:
    """Initialize service with given config. Returns status."""
    errors = validate_config(config)
    if errors:
        return {{"started": False, "errors": errors}}
    return {{"started": True, "config_keys": list(config.keys())}}
'''

    def _gen_reconcile_stub(self, svc: dict) -> str:
        config_file = svc["config_file"]
        return f'''\
"""
Config reconciliation tool.

TODO: Implement reconcile_to_vcs() to:
1. Load the VCS reference config (config/vcs_config.json)
2. Identify all keys in production config that differ from VCS
3. Update production config to match VCS exactly
4. Write the reconciled config back to {config_file}
5. Return a summary of changes made

The function must NOT modify config/vcs_config.json.
"""
import json
import os
from service import load_config, diff_configs

CONFIG_FILE = "{config_file}"
VCS_CONFIG_FILE = "config/vcs_config.json"


def reconcile_to_vcs() -> dict:
    """Reconcile production config to match VCS state.

    Returns:
        dict with keys:
          - "changes": dict of {{key: {{"from": old_val, "to": new_val}}}}
          - "removed": list of keys removed (extra keys not in VCS)
          - "config_file": path that was updated
    """
    # TODO: Implement reconciliation
    # Stub returns empty — no changes made
    return {{
        "changes": {{}},
        "removed": [],
        "config_file": CONFIG_FILE,
    }}


if __name__ == "__main__":
    result = reconcile_to_vcs()
    print(f"Reconciliation complete:")
    print(f"  Changed {{len(result['changes'])}} keys")
    print(f"  Removed {{len(result['removed'])}} keys")
    for key, change in result["changes"].items():
        print(f"  {{key}}: {{change['from']!r}} → {{change['to']!r}}")
    for key in result["removed"]:
        print(f"  REMOVED: {{key}}")
'''

    def _gen_tests(self, svc: dict, prod_config: dict, extra_key: str) -> str:
        vcs_json = json.dumps(svc["vcs_config"])
        drift_targets = svc["drift_targets"]
        drift_values = svc["drift_values"]
        return f'''\
"""
Config drift reconciliation tests.

Tests verify that:
1. Drifted config is correctly identified
2. reconcile_to_vcs() fixes all drifted keys
3. Extra keys (not in VCS) are removed
4. VCS config file is not modified
5. Service starts cleanly after reconciliation
"""
import json
import os
import shutil
import pytest

# Make config directory available
os.makedirs("config", exist_ok=True)

import service as svc_module
import reconcile as rec_module


VCS_CONFIG = {vcs_json}
DRIFT_KEYS = {drift_targets!r}
EXTRA_KEY = "{extra_key}"


@pytest.fixture(autouse=True)
def restore_configs(tmp_path):
    """Restore production config to drifted state before each test."""
    os.makedirs("config", exist_ok=True)
    # Write drifted production config (as deployed)
    prod = dict(VCS_CONFIG)
    for key, val in zip({drift_targets!r}, {drift_values!r}):
        prod[key] = val
    prod[EXTRA_KEY] = True
    with open("{svc["config_file"]}", "w") as f:
        json.dump(prod, f, indent=2)
    # Write VCS reference config
    with open("config/vcs_config.json", "w") as f:
        json.dump(VCS_CONFIG, f, indent=2)
    yield
    # Clean up
    for p in ["{svc["config_file"]}", "config/vcs_config.json"]:
        if os.path.exists(p):
            os.remove(p)


def test_diff_detects_all_drifted_keys():
    """diff_configs() must detect all drifted keys."""
    prod = svc_module.load_config("{svc["config_file"]}")
    vcs = svc_module.load_config("config/vcs_config.json")
    diffs = svc_module.diff_configs(prod, vcs)

    for key in DRIFT_KEYS:
        assert key in diffs, f"Drift key '{{key}}' not detected in diff"
    assert EXTRA_KEY in diffs, f"Extra key '{{EXTRA_KEY}}' not detected in diff"


def test_reconcile_fixes_all_drifted_keys():
    """After reconcile_to_vcs(), all drifted keys must match VCS."""
    result = rec_module.reconcile_to_vcs()

    reconciled = svc_module.load_config("{svc["config_file"]}")
    for key in DRIFT_KEYS:
        assert reconciled[key] == VCS_CONFIG[key], (
            f"Key '{{key}}' not reconciled: got {{reconciled[key]!r}}, expected {{VCS_CONFIG[key]!r}}"
        )


def test_reconcile_removes_extra_keys():
    """After reconcile_to_vcs(), extra keys not in VCS must be removed."""
    rec_module.reconcile_to_vcs()
    reconciled = svc_module.load_config("{svc["config_file"]}")
    assert EXTRA_KEY not in reconciled, (
        f"Extra key '{{EXTRA_KEY}}' still present after reconciliation"
    )


def test_vcs_config_not_modified():
    """reconcile_to_vcs() must NOT modify config/vcs_config.json."""
    import hashlib
    with open("config/vcs_config.json") as f:
        before = f.read()
    rec_module.reconcile_to_vcs()
    with open("config/vcs_config.json") as f:
        after = f.read()
    assert json.loads(before) == json.loads(after), (
        "VCS config was modified — reconcile must only update production config"
    )


def test_service_starts_after_reconciliation():
    """Service must start cleanly after reconciliation."""
    rec_module.reconcile_to_vcs()
    config = svc_module.load_config("{svc["config_file"]}")
    status = svc_module.start_service(config)
    assert status["started"] is True, (
        f"Service failed to start after reconciliation: {{status.get('errors')}}"
    )


def test_reconcile_returns_change_summary():
    """reconcile_to_vcs() must return a dict with changes and removed keys."""
    result = rec_module.reconcile_to_vcs()
    assert "changes" in result, "reconcile_to_vcs() must return 'changes' key"
    assert "removed" in result, "reconcile_to_vcs() must return 'removed' key"
    assert EXTRA_KEY in result["removed"] or EXTRA_KEY in result["changes"], (
        f"Extra key '{{EXTRA_KEY}}' not reported in reconcile result"
    )


def test_validate_config_clean_after_reconcile():
    """validate_config() must return no errors after reconciliation."""
    rec_module.reconcile_to_vcs()
    config = svc_module.load_config("{svc["config_file"]}")
    errors = svc_module.validate_config(config)
    assert not errors, f"Config still invalid after reconciliation: {{errors}}"
'''

    def _gen_spec(self, svc: dict, prod_config: dict, extra_key: str) -> str:
        drifted = {}
        for key, val in zip(svc["drift_targets"], svc["drift_values"]):
            drifted[key] = {"production": val, "vcs": svc["vcs_config"][key]}
        drifted[extra_key] = {"production": True, "vcs": "<NOT IN VCS>"}

        drift_table = "\n".join(
            f"| `{k}` | `{v['production']}` | `{v['vcs']}` |"
            for k, v in drifted.items()
        )

        return f"""# RINC10: Config Drift — Production vs Version Control

## Incident Background
Inspired by multiple incidents where manual production config changes were
never committed back to version control. The Knight Capital Group incident
(2012) and numerous cloud service outages followed this pattern. Engineers
make emergency changes, mark them "temporary", and never revert.

## Service: {svc["service"]}
Config file: `{svc["config_file"]}`
VCS reference: `config/vcs_config.json`

## Symptom
{svc["monitoring_symptom"]}

## Root Cause
{svc["drift_explanation"]}

See `corpus/deployment_log.txt` for the timeline of manual changes.

## Drifted Configuration

| Key | Production (wrong) | VCS (correct) |
|-----|-------------------|---------------|
{drift_table}

## Required Fix: Implement `reconcile_to_vcs()` in `reconcile.py`

The function must:
1. Load VCS reference config from `config/vcs_config.json`
2. Load current production config from `{svc["config_file"]}`
3. For each key in VCS: update production to match VCS value
4. Remove any extra keys in production that are not in VCS
5. Write reconciled config back to `{svc["config_file"]}`
6. Return `{{"changes": {{...}}, "removed": [...], "config_file": "..."}}`

**Do NOT modify** `config/vcs_config.json` — it is the source of truth.

## Acceptance Criteria
1. All {len(svc["drift_targets"])} drifted keys corrected to VCS values
2. Extra key `{extra_key}` removed from production config
3. `config/vcs_config.json` unchanged
4. `validate_config()` returns no errors after reconciliation
5. Service starts cleanly after reconciliation
6. `reconcile_to_vcs()` returns accurate change summary
7. All tests pass: `pytest test_config.py -v`

## Files
- `reconcile.py` — implement `reconcile_to_vcs()`
- `service.py` — do NOT modify
- `test_config.py` — do NOT modify
- `config/vcs_config.json` — do NOT modify (source of truth)
"""

    def _gen_brief(self, svc: dict) -> str:
        return f"""# RINC10: Config Drift Fix (Brief)

The {svc["service"]} is misbehaving in production. Monitoring shows:
{svc["monitoring_symptom"]}

Engineering suspects the production config has diverged from version control.
The VCS reference is at `config/vcs_config.json`.

Implement `reconcile_to_vcs()` in `reconcile.py` to fix the production config.

Verify with:
```
pytest test_config.py -v
```

**Files to fix:** `reconcile.py`
**Do NOT modify:** `service.py`, `test_config.py`, `config/vcs_config.json`
"""
