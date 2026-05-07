"""
Config reconciliation tool.

TODO: Implement reconcile_to_vcs() to:
1. Load the VCS reference config (config/vcs_config.json)
2. Identify all keys in production config that differ from VCS
3. Update production config to match VCS exactly
4. Write the reconciled config back to config/feature_flags.json
5. Return a summary of changes made

The function must NOT modify config/vcs_config.json.
"""
import json
import os
from service import load_config, diff_configs

CONFIG_FILE = "config/feature_flags.json"
VCS_CONFIG_FILE = "config/vcs_config.json"


def reconcile_to_vcs() -> dict:
    """Reconcile production config to match VCS state.

    Returns:
        dict with keys:
          - "changes": dict of {key: {"from": old_val, "to": new_val}}
          - "removed": list of keys removed (extra keys not in VCS)
          - "config_file": path that was updated
    """
    # TODO: Implement reconciliation
    # Stub returns empty — no changes made
    return {
        "changes": {},
        "removed": [],
        "config_file": CONFIG_FILE,
    }


if __name__ == "__main__":
    result = reconcile_to_vcs()
    print(f"Reconciliation complete:")
    print(f"  Changed {len(result['changes'])} keys")
    print(f"  Removed {len(result['removed'])} keys")
    for key, change in result["changes"].items():
        print(f"  {key}: {change['from']!r} → {change['to']!r}")
    for key in result["removed"]:
        print(f"  REMOVED: {key}")
