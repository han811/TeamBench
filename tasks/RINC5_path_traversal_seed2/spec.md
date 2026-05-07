# RINC5: Path Traversal Vulnerability

## Incident Background
Inspired by CWE-22 (Path Traversal) — one of the most consistently exploited
vulnerability classes. File download endpoints that don't normalize paths allow
attackers to read arbitrary files on the server.

## Service: ReportExporter
File: `app.py` | Base directory: `reports/`

## Vulnerability
**Technique:** null_byte
**Description:** null byte injection terminates path string in C-based functions: report.pdf\x00/../../../etc/passwd

**Vulnerable function:**
```python
def resolve_file_path(filename: str) -> str:
    path = os.path.join(BASE_DIR, filename)
    # No realpath() normalization, no prefix check
    return path
```

**Attack:**
```
GET /export?report=../../../../etc/passwd
→ Returns contents of /etc/passwd
```

## Required Fix
reject filenames containing null bytes (\x00) and normalize with os.path.realpath()

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
Files available in `reports/`: `report_193.txt`, `data_186.csv`, `export_469.json`

## Acceptance Criteria
1. `/export?report=../../etc/passwd` → 400/403/404
2. `/export?report=../../../../etc/shadow` → 400/403/404
3. `/export?report=/etc/passwd` → 400/403/404
4. `/export?report=report_193.txt` → 200 (legitimate file works)
5. `resolve_file_path()` does not return paths outside `reports/`
6. All tests pass: `pytest test_traversal.py -v`

## Files
- `app.py` — fix `resolve_file_path()` function
- `setup_files.py` — do NOT modify
- `test_traversal.py` — do NOT modify
