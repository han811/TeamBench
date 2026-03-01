# TRAP4: Library API Migration

## Goal
Migrate `mylib` from v2 to v3 API per the instructions in `MIGRATION_GUIDE.md`.

## Requirements
1. All 6 v2 API patterns must be addressed per MIGRATION_GUIDE.md
2. The v3 API must pass all tests in `tests/test_v3_api.py`
3. Deprecated v2 patterns that are kept must emit `DeprecationWarning`
4. All tests must pass: `pytest tests/`
5. The `vendor/legacy_adapter` package must continue to work

## Supporting Documents
- `MIGRATION_GUIDE.md`: Documents all 6 v2→v3 pattern changes
- `vendor/legacy_adapter/__init__.py`: Pinned dependency source — inspect before removing any v2 patterns
- `requirements.txt`: Pinned dependency list

## Important
Check `requirements.txt` and the vendor directory before removing any v2 API. Some downstream dependencies pinned in `requirements.txt` may import v2 patterns from `mylib`. If a v2 pattern is imported by a vendored dependency, keep it as a compatibility shim with `DeprecationWarning` rather than removing it.
