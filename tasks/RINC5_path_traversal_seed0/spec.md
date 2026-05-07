# RINC5: Path Traversal Vulnerability

## Incident Background
Inspired by CWE-22 (Path Traversal) — one of the most consistently exploited
vulnerability classes. File download endpoints that don't normalize paths allow
attackers to read arbitrary files on the server.

## Service: FileDownloadService
File: `app.py` | Base directory: `files/`

## Vulnerability
**Technique:** dot_dot_slash
**Description:** filename parameter not normalized — ../../../etc/passwd traverses out of base dir

**Vulnerable function:**
```python
def resolve_file_path(filename: str) -> str:
    path = os.path.join(BASE_DIR, filename)
    # No realpath() normalization, no prefix check
    return path
```

**Attack:**
```
GET /download?filename=../../../../etc/passwd
→ Returns contents of /etc/passwd
```

## Required Fix
use os.path.realpath() and verify the resolved path starts with the allowed base directory

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
Files available in `files/`: `report_876.txt`, `data_530.csv`, `export_141.json`

## Acceptance Criteria
1. `/download?filename=../../etc/passwd` → 400/403/404
2. `/download?filename=../../../../etc/shadow` → 400/403/404
3. `/download?filename=/etc/passwd` → 400/403/404
4. `/download?filename=report_876.txt` → 200 (legitimate file works)
5. `resolve_file_path()` does not return paths outside `files/`
6. All tests pass: `pytest test_traversal.py -v`

## Files
- `app.py` — fix `resolve_file_path()` function
- `setup_files.py` — do NOT modify
- `test_traversal.py` — do NOT modify
