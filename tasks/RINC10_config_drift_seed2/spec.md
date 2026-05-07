# RINC10: Config Drift — Production vs Version Control

## Incident Background
Inspired by multiple incidents where manual production config changes were
never committed back to version control. The Knight Capital Group incident
(2012) and numerous cloud service outages followed this pattern. Engineers
make emergency changes, mark them "temporary", and never revert.

## Service: DatabasePoolService
Config file: `config/db_pool.json`
VCS reference: `config/vcs_config.json`

## Symptom
connection pool exhaustion p99 latency 8s — max_connections too low, SSL disabled

## Root Cause
max_connections reduced to debug pool exhaustion, SSL disabled to bypass cert issue, neither reverted

See `corpus/deployment_log.txt` for the timeline of manual changes.

## Drifted Configuration

| Key | Production (wrong) | VCS (correct) |
|-----|-------------------|---------------|
| `max_connections` | `5` | `50` |
| `connection_timeout_ms` | `500` | `5000` |
| `enable_ssl` | `False` | `True` |
| `debug_mode` | `True` | `<NOT IN VCS>` |

## Required Fix: Implement `reconcile_to_vcs()` in `reconcile.py`

The function must:
1. Load VCS reference config from `config/vcs_config.json`
2. Load current production config from `config/db_pool.json`
3. For each key in VCS: update production to match VCS value
4. Remove any extra keys in production that are not in VCS
5. Write reconciled config back to `config/db_pool.json`
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
