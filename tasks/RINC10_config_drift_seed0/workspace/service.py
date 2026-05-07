"""
RateLimiterService: Loads and validates its configuration.

The service reads from config/rate_limiter.json. Production config has drifted
from the VCS-controlled reference (config/vcs_config.json).
"""
import json
import os


CONFIG_FILE = "config/rate_limiter.json"
VCS_CONFIG_FILE = "config/vcs_config.json"


def load_config(path: str = CONFIG_FILE) -> dict:
    """Load configuration from JSON file."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found: {path}")
    with open(path) as f:
        return json.load(f)


def validate_config(config: dict) -> list[str]:
    """Validate config keys and types. Returns list of error strings."""
    errors = []
    vcs = load_config(VCS_CONFIG_FILE)

    # Check for missing keys
    for key in vcs:
        if key not in config:
            errors.append(f"Missing key: {key}")

    # Check for extra keys not in VCS spec
    for key in config:
        if key not in vcs:
            errors.append(f"Extra key not in VCS spec: {key}")

    # Check types match
    for key in vcs:
        if key in config and type(config[key]) != type(vcs[key]):
            errors.append(f"Type mismatch for {key}: expected {type(vcs[key]).__name__}, got {type(config[key]).__name__}")

    return errors


def diff_configs(production: dict, vcs: dict) -> dict:
    """Compare production config to VCS config, return differences."""
    diffs = {}
    all_keys = set(production) | set(vcs)
    for key in all_keys:
        prod_val = production.get(key, "<MISSING>")
        vcs_val = vcs.get(key, "<MISSING>")
        if prod_val != vcs_val:
            diffs[key] = {"production": prod_val, "vcs": vcs_val}
    return diffs


def start_service(config: dict) -> dict:
    """Initialize service with given config. Returns status."""
    errors = validate_config(config)
    if errors:
        return {"started": False, "errors": errors}
    return {"started": True, "config_keys": list(config.keys())}
