# Analysis Guidance — TRAP4_version_paradox

## Tools to run
- `cat MIGRATION_GUIDE.md` — read all 6 v2→v3 changes
- `cat vendor/legacy_adapter/__init__.py` — CRITICAL: find which v2 patterns are imported
- `grep -r "from mylib import\|import mylib" vendor/` — trace all vendor imports
- `cat requirements.txt`

## Key Finding
`vendor/legacy_adapter/__init__.py` imports two v2 patterns:
- `connect_v2` (v2 connection factory)
- `QueryBuilder` (v2 query builder class)

If you remove these from `mylib/__init__.py`, the adapter fails to import and
`tests/test_adapter.py` fails immediately.

## Tell Executor

**Fully migrate (4 patterns)**:
- `execute()` → `run()` (rename)
- `fetch_all()` → `results()` (rename)
- `set_config()` → `configure()` (renamed + new signature)
- `RawQuery` → `Query` (class rename)

**Keep as compatibility shims in `mylib/compat.py` (2 patterns)**:
- `connect_v2` → delegate to `connect()` with DeprecationWarning
- `QueryBuilder` → subclass of `Builder` with DeprecationWarning in `__init__`

Move shims to `mylib/compat.py` and re-export from `mylib/__init__.py` with a deprecation note.
