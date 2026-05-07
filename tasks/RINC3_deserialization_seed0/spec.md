# RINC3: Unsafe Deserialization — PICKLE

## Incident Background
Inspired by multiple CVEs involving unsafe deserialization in Python applications.
The `pickle` vector allows attackers to execute arbitrary code on the server
by sending a crafted payload to the `/submit` endpoint.

## Service: TaskQueueService
File: `app.py`

## Vulnerability
**Location:** `/submit` route handler in `app.py`
**Unsafe operation:** `pickle.loads(data)`
**Attack:** arbitrary Python object deserialization — any class with __reduce__ can execute code

**Concrete attack payload:**
```
POST /submit
payload=<malicious_pickle_payload>
```
A crafted payload causes the server to execute arbitrary OS commands.

## Required Fix
replace pickle.loads() with json.loads() for untrusted input

Replace:
```python
pickle.loads(data)
```
With the safe alternative that only handles data types, not code execution.

## Acceptance Criteria
1. A malicious `pickle` payload does NOT execute code (no /tmp/pwned file)
2. Normal `pickle` data continues to be processed correctly
3. The unsafe call `pickle.loads(data)` no longer appears in `app.py`
4. Missing/malformed input returns 400
5. All tests pass: `pytest test_deser.py -v`

## Files
- `app.py` — fix the unsafe deserialization call
- `test_deser.py` — do NOT modify
