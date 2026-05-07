# RINC10: Config Drift — Production vs Version Control

## Incident Background
Inspired by multiple incidents where manual production config changes were
never committed back to version control. The Knight Capital Group incident
(2012) and numerous cloud service outages followed this pattern. Engineers
make emergency changes, mark them "temporary", and never revert.

## Service: FeatureFlagService
Config file: `config/feature_flags.json`
VCS reference: `config/vcs_config.json`

## Symptom
checkout conversion 60% below normal — new checkout flow disabled in production

## Root Cause
checkout feature disabled for hotfix, AB test % reduced for incident, never re-enabled

See `corpus/deployment_log.txt` for the timeline of manual changes.

## Drifted Configuration

| Key | Production (wrong) | VCS (correct) |
|-----|-------------------|---------------|
| `enable_new_checkout` | `False` | `True` |
| `ab_test_percentage` | `5` | `50` |
| `cache_ttl_seconds` | `30` | `300` |
| `debug_mode` | `True` | `<NOT IN VCS>` |

## Required Fix: Implement `reconcile_to_vcs()` in `reconcile.py`

The function must:
1. Load VCS reference config from `config/vcs_config.json`
2. Load current production config from `config/feature_flags.json`
3. For each key in VCS: update production to match VCS value
4. Remove any extra keys in production that are not in VCS
5. Write reconciled config back to `config/feature_flags.json`
6. Return `{"changes": {...}, "removed": [...], "config_file": "..."}`

**Do NOT modify** `config/vcs_config.json` — it is the source of truth.

## Acceptance Criteria
1. All 3 drifted keys corrected to VCS values
2. Extra key `debug_mode` removed from production config
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
