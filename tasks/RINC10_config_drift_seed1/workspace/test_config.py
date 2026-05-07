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


VCS_CONFIG = {"enable_new_checkout": true, "enable_recommendations": true, "enable_dark_mode": false, "ab_test_percentage": 50, "max_items_per_page": 25, "cache_ttl_seconds": 300, "enable_analytics": true}
DRIFT_KEYS = ['enable_new_checkout', 'ab_test_percentage', 'cache_ttl_seconds']
EXTRA_KEY = "debug_mode"


@pytest.fixture(autouse=True)
def restore_configs(tmp_path):
    """Restore production config to drifted state before each test."""
    os.makedirs("config", exist_ok=True)
    # Write drifted production config (as deployed)
    prod = dict(VCS_CONFIG)
    for key, val in zip(['enable_new_checkout', 'ab_test_percentage', 'cache_ttl_seconds'], [False, 5, 30]):
        prod[key] = val
    prod[EXTRA_KEY] = True
    with open("config/feature_flags.json", "w") as f:
        json.dump(prod, f, indent=2)
    # Write VCS reference config
    with open("config/vcs_config.json", "w") as f:
        json.dump(VCS_CONFIG, f, indent=2)
    yield
    # Clean up
    for p in ["config/feature_flags.json", "config/vcs_config.json"]:
        if os.path.exists(p):
            os.remove(p)


def test_diff_detects_all_drifted_keys():
    """diff_configs() must detect all drifted keys."""
    prod = svc_module.load_config("config/feature_flags.json")
    vcs = svc_module.load_config("config/vcs_config.json")
    diffs = svc_module.diff_configs(prod, vcs)

    for key in DRIFT_KEYS:
        assert key in diffs, f"Drift key '{key}' not detected in diff"
    assert EXTRA_KEY in diffs, f"Extra key '{EXTRA_KEY}' not detected in diff"


def test_reconcile_fixes_all_drifted_keys():
    """After reconcile_to_vcs(), all drifted keys must match VCS."""
    result = rec_module.reconcile_to_vcs()

    reconciled = svc_module.load_config("config/feature_flags.json")
    for key in DRIFT_KEYS:
        assert reconciled[key] == VCS_CONFIG[key], (
            f"Key '{key}' not reconciled: got {reconciled[key]!r}, expected {VCS_CONFIG[key]!r}"
        )


def test_reconcile_removes_extra_keys():
    """After reconcile_to_vcs(), extra keys not in VCS must be removed."""
    rec_module.reconcile_to_vcs()
    reconciled = svc_module.load_config("config/feature_flags.json")
    assert EXTRA_KEY not in reconciled, (
        f"Extra key '{EXTRA_KEY}' still present after reconciliation"
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
    config = svc_module.load_config("config/feature_flags.json")
    status = svc_module.start_service(config)
    assert status["started"] is True, (
        f"Service failed to start after reconciliation: {status.get('errors')}"
    )


def test_reconcile_returns_change_summary():
    """reconcile_to_vcs() must return a dict with changes and removed keys."""
    result = rec_module.reconcile_to_vcs()
    assert "changes" in result, "reconcile_to_vcs() must return 'changes' key"
    assert "removed" in result, "reconcile_to_vcs() must return 'removed' key"
    assert EXTRA_KEY in result["removed"] or EXTRA_KEY in result["changes"], (
        f"Extra key '{EXTRA_KEY}' not reported in reconcile result"
    )


def test_validate_config_clean_after_reconcile():
    """validate_config() must return no errors after reconciliation."""
    rec_module.reconcile_to_vcs()
    config = svc_module.load_config("config/feature_flags.json")
    errors = svc_module.validate_config(config)
    assert not errors, f"Config still invalid after reconciliation: {errors}"
