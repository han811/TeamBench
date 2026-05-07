# RINC3: Unsafe Deserialization — YAML_LOAD

## Incident Background
Inspired by multiple CVEs involving unsafe deserialization in Python applications.
The `yaml_load` vector allows attackers to execute arbitrary code on the server
by sending a crafted payload to the `/load-config` endpoint.

## Service: ConfigLoaderService
File: `app.py`

## Vulnerability
**Location:** `/load-config` route handler in `app.py`
**Unsafe operation:** `yaml.load(data, Loader=yaml.Loader)`
**Attack:** yaml.load() with full Loader allows !!python/object tags that execute arbitrary code

**Concrete attack payload:**
```
POST /load-config
config=<malicious_yaml_payload>
```
A crafted payload causes the server to execute arbitrary OS commands.

## Required Fix
replace yaml.load(..., Loader=yaml.Loader) with yaml.safe_load()

Replace:
```python
yaml.load(data, Loader=yaml.Loader)
```
With the safe alternative that only handles data types, not code execution.

## Acceptance Criteria
1. A malicious `yaml_load` payload does NOT execute code (no /tmp/pwned file)
2. Normal `yaml` data continues to be processed correctly
3. The unsafe call `yaml.load(data, Loader=yaml.Loader)` no longer appears in `app.py`
4. Missing/malformed input returns 400
5. All tests pass: `pytest test_deser.py -v`

## Files
- `app.py` — fix the unsafe deserialization call
- `test_deser.py` — do NOT modify
