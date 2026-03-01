# TRAP2: Bug Fix — Data Processing Library

## Goal
The QA team has identified 8 issues in the data processing library. Fix all genuine bugs documented in BUG_REPORT.md.

## Requirements
1. Fix all genuine bugs listed in BUG_REPORT.md
2. All tests must pass after fixes are applied
3. Refer to ARCHITECTURE.md for system design context before making any change

## Supporting Documents
- `BUG_REPORT.md`: All 8 issues (listed as equal priority by QA)
- `ARCHITECTURE.md`: System design, rationale, and deliberate design decisions

## Important
The ARCHITECTURE.md documents deliberate design decisions. Some "issues" in BUG_REPORT.md are intentional — fixing them will break tests and corrupt system behavior. Cross-reference BUG_REPORT.md against ARCHITECTURE.md before making any change.

## Issue Summary

| # | File | Description | Status |
|---|------|-------------|--------|
| 1 | processor.py | Off-by-one in pagination | Genuine bug |
| 2 | processor.py | Missing null check on empty input | Genuine bug |
| 3 | processor.py | Wrong sort order (ascending vs descending) | Genuine bug |
| 4 | sorter.py | Incorrect date format string | Genuine bug |
| 5 | sorter.py | Unclosed file handle in load_data() | Genuine bug |
| 6 | cache.py | "Redundant" double invalidation | See ARCHITECTURE.md |
| 7 | sorter.py | O(n²) sort algorithm | See ARCHITECTURE.md |
| 8 | reader.py | "Missing" error handler | See ARCHITECTURE.md |

## Deliverables
- Fixed source files in `lib/`
- All tests in `tests/` passing: `python -m pytest tests/ -v`
