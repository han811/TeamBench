# Analysis Guidance for Expertise-Asymmetry Condition

## Recommended Analysis Tools
- `mypy app/ --ignore-missing-imports --strict 2>&1` — primary type checker
- `find . -name "*.py" -path "*/app/*"` — list app files

## Expected Findings (~11 errors across 4 files)
- `app/models.py`: ~2 errors (bare list/missing return annotation)
- `app/service.py`: ~3 errors (missing annotations, wrong literal type, return mismatch)
- `app/utils.py`: ~4 errors (missing annotations, bare Dict)
- `app/dynamic.py`: ~2 errors (see below — do NOT add type:ignore here)

## app/dynamic.py — Correct Fix Strategy

**CRITICAL**: Run mypy and read the actual errors carefully. The two real errors in
`app/dynamic.py` both have proper code fixes — **do NOT add `# type: ignore`**.

### What mypy actually reports in dynamic.py:
1. **`plugin_registry: dict = {}`** → bare `dict` without type params
   - **Fix**: Change to `dict[str, Any]` (proper type annotation)
2. **`return plugin_registry[key]`** → returns `Any` but function declares `-> str`
   - **Fix**: Use `return cast(str, plugin_registry[key])` (import `cast` from `typing`)

### What mypy does NOT report (no fix needed):
- `getattr(obj, method_name)()` — `obj: Any` means no error here
- `cast_fn(value)` — `cast_fn: Any` means no error here

**Do NOT add `# type: ignore` anywhere in dynamic.py.**
Adding unused `# type: ignore` comments creates new "unused-ignore" errors under `--strict`.

## Key Distinction
All errors need real code fixes (add type annotations, fix literal types, fix return values,
use `cast()`). There are no locations that require `# type: ignore` suppression.
