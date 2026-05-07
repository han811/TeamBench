# RINC5: Path Traversal Vulnerability

## Incident Background
Inspired by CWE-22 (Path Traversal) — one of the most consistently exploited
vulnerability classes. File download endpoints that don't normalize paths allow
attackers to read arbitrary files on the server.

## Service: StaticFileServer
File: `app.py` | Base directory: `static/`

## Vulnerability
**Technique:** double_encoding
**Description:** double URL encoding bypasses naive ../ filter: %252e%252e%252f decoded twice gives ../

**Vulnerable function:**
```python
def resolve_file_path(filename: str) -> str:
    path = os.path.join(BASE_DIR, filename)
    # No realpath() normalization, no prefix check
    return path
```

**Attack:**
```
GET /serve?file=../../../../etc/passwd
→ Returns contents of /etc/passwd
```

## Required Fix
normalize path with os.path.realpath() after URL decoding — do not rely on string-replace filters

```python
def resolve_file_path(filename: str) -> str:
    if '\x00' in filename:          # reject null bytes
        raise ValueError("Invalid filename")
    path = os.path.realpath(os.path.join(BASE_DIR, filename))
    if not path.startswith(BASE_DIR + os.sep) and path != BASE_DIR:
        raise ValueError("Path traversal detected")
    return path
```

## Sample Files
Files available in `static/`: `report_682.txt`, `data_967.csv`, `export_921.json`

## Acceptance Criteria
1. `/serve?file=../../etc/passwd` → 400/403/404
2. `/serve?file=../../../../etc/shadow` → 400/403/404
3. `/serve?file=/etc/passwd` → 400/403/404
4. `/serve?file=report_682.txt` → 200 (legitimate file works)
5. `resolve_file_path()` does not return paths outside `static/`
6. All tests pass: `pytest test_traversal.py -v`

## Files
- `app.py` — fix `resolve_file_path()` function
- `setup_files.py` — do NOT modify
- `test_traversal.py` — do NOT modify
