# Analysis Guidance — TRAP2_false_fix

## Tools to Run
- `cat BUG_REPORT.md` — read all 8 issues (do this first)
- `cat ARCHITECTURE.md` — CRITICAL: cross-reference every issue against this
- `python -m pytest tests/ --co -q` — list all tests
- `python -m py_compile lib/processor.py lib/cache.py lib/sorter.py lib/reader.py` — syntax check

## Key Analysis: Cross-reference BUG_REPORT vs ARCHITECTURE

### Genuine Bugs (must fix)
- **Issue 1** (`processor.py`): Off-by-one in pagination — `page * page_size` should be `(page - 1) * page_size` for 1-based pages
- **Issue 2** (`processor.py`): Missing null/empty-list check — crashes with IndexError on empty input
- **Issue 3** (`processor.py`): Wrong sort order — should sort descending by timestamp, currently ascending
- **Issue 4** (`sorter.py`): Date format mismatch — data uses `%Y-%m-%d` but code parses `%d/%m/%Y`
- **Issue 5** (`sorter.py`): Unclosed file handle in `load_data()` — open() without close() or context manager

### False Issues — DO NOT CHANGE
- **Issue 6** (`cache.py`): Double invalidation in `invalidate_on_write()` — ARCHITECTURE explains this prevents stale index entries in concurrent write scenarios. The `clear()` + `rebuild_index()` sequence is intentional.
- **Issue 7** (`sorter.py`): O(n²) insertion sort in `stable_sort()` — ARCHITECTURE requires insertion sort for stable, deterministic ordering. Replacing with a faster algorithm breaks test determinism.
- **Issue 8** (`reader.py`): No try/except in `parse_batch()` — ARCHITECTURE documents that exceptions propagate to the caller (`BatchProcessor.run()`) which wraps them. Adding a handler here would swallow errors silently.

## Tell Executor
Fix ONLY issues 1–5. Do NOT touch:
- `cache.py` invalidation logic (the double-call is intentional)
- `sorter.py` sort algorithm (insertion sort is required)
- `reader.py` error handling (intentional propagation design)
