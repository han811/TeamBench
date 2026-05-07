# RINC5: Path Traversal Fix (Brief)

The FileDownloadService's `/download` endpoint has been flagged — it may
allow access to files outside the intended `files/` directory.

Fix the file path resolution in `app.py`.

Setup and verify with:
```
python setup_files.py
pytest test_traversal.py -v
```

**Files to fix:** `app.py`
**Do NOT modify:** `setup_files.py`, `test_traversal.py`
