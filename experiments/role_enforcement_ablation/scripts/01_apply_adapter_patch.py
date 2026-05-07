"""01_apply_adapter_patch.py — Add Google provider pinning to openai_adapter.py.

Why
---
`harness/adapters/openai_adapter.py` pins Anthropic-via-OpenRouter to the
`anthropic` provider with `allow_fallbacks=false` (lines 182-187, 371-374).
This preserves prompt caching semantics and keeps run-to-run behavior
deterministic. Google-via-OR has no equivalent pinning, so `gemini-3-flash`
can be routed to `google-ai-studio` on one run and to Vertex AI on the next.

For a reproducibility-critical experiment, this is unacceptable. This script
adds a parallel `_is_or_google` flag with the matching provider-pin branch.

Properties
----------
- **Idempotent**: re-running is safe. Detects the existing patch by marker
  string `_is_or_google` in the target file.
- **Reversible**: call with `--revert` to restore from the timestamped backup
  created during apply. `99_replicate_from_scratch.sh` calls `--revert` at
  the end of the pipeline so the repo state is unchanged after replication.
- **Surgical**: two string-level edits, no AST manipulation. The patched code
  is unit-tested by `scripts/smoke_test_real_llm.py`.

Invocation
----------
    apply:  python scripts/01_apply_adapter_patch.py
    revert: python scripts/01_apply_adapter_patch.py --revert
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
TARGET = REPO_ROOT / "harness" / "adapters" / "openai_adapter.py"
PATCH_MARKER = "_is_or_google"

# --- Patch 1: add _is_or_google flag next to _is_or_anthropic ---------------
ANCHOR_FLAG = (
    '        self._is_or_anthropic = bool(\n'
    '            base_url and "openrouter.ai" in base_url\n'
    '            and model.startswith("anthropic/")\n'
    '        )\n'
    '        if self._is_or_anthropic:\n'
    '            print(f"  [openrouter-anthropic] prompt caching enabled for {model}")\n'
)
REPLACEMENT_FLAG = ANCHOR_FLAG + (
    '        # role_enforcement_ablation patch: pin Google-via-OR to a single\n'
    '        # back-end provider so `gemini-3-flash` routing stays deterministic.\n'
    '        self._is_or_google = bool(\n'
    '            base_url and "openrouter.ai" in base_url\n'
    '            and model.startswith("google/")\n'
    '        )\n'
    '        if self._is_or_google:\n'
    '            print(f"  [openrouter-google] provider pinned to google-ai-studio for {model}")\n'
)

# --- Patch 2: inject provider pin in _call_with_retry -----------------------
ANCHOR_PIN = (
    '        if self._is_or_anthropic:\n'
    '            extra = kwargs.get("extra_body") or {}\n'
    '            extra.setdefault("provider", {"order": ["anthropic"], "allow_fallbacks": False})\n'
    '            kwargs["extra_body"] = extra\n'
)
REPLACEMENT_PIN = ANCHOR_PIN + (
    '        # role_enforcement_ablation patch: symmetric pin for Google-via-OR.\n'
    '        elif self._is_or_google:\n'
    '            extra = kwargs.get("extra_body") or {}\n'
    '            extra.setdefault("provider", {"order": ["google-ai-studio"], "allow_fallbacks": False})\n'
    '            kwargs["extra_body"] = extra\n'
)


def find_backup() -> Path | None:
    """Return the most recent backup file, or None."""
    backups = sorted(TARGET.parent.glob("openai_adapter.py.bak_*"))
    return backups[-1] if backups else None


def is_applied(src: str) -> bool:
    return PATCH_MARKER in src


def apply_patch() -> int:
    if not TARGET.exists():
        print(f"ERROR: target not found: {TARGET}", file=sys.stderr)
        return 2

    original = TARGET.read_text(encoding="utf-8")
    if is_applied(original):
        print(f"[patch] already applied (marker {PATCH_MARKER!r} present) — no-op")
        return 0

    if ANCHOR_FLAG not in original:
        print(f"ERROR: anchor for patch 1 (flag block) not found in {TARGET}",
              file=sys.stderr)
        print("       The file may have drifted. Inspect manually before re-running.",
              file=sys.stderr)
        return 3
    if ANCHOR_PIN not in original:
        print(f"ERROR: anchor for patch 2 (pin block) not found in {TARGET}",
              file=sys.stderr)
        return 4

    # Timestamped backup before editing
    ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    backup = TARGET.parent / f"openai_adapter.py.bak_{ts}"
    shutil.copy2(TARGET, backup)
    print(f"[patch] backup written: {backup}")

    patched = original.replace(ANCHOR_FLAG, REPLACEMENT_FLAG, 1)
    patched = patched.replace(ANCHOR_PIN, REPLACEMENT_PIN, 1)
    TARGET.write_text(patched, encoding="utf-8")

    # Sanity: confirm marker present and file still parses
    if not is_applied(TARGET.read_text(encoding="utf-8")):
        print("ERROR: patch did not land (marker missing after write)", file=sys.stderr)
        shutil.copy2(backup, TARGET)
        return 5
    try:
        import py_compile
        py_compile.compile(str(TARGET), doraise=True)
    except py_compile.PyCompileError as e:
        print(f"ERROR: patched file does not compile: {e}", file=sys.stderr)
        shutil.copy2(backup, TARGET)
        return 6

    print(f"[patch] applied cleanly")
    print(f"[patch] marker: {PATCH_MARKER}")
    print(f"[patch] backup: {backup.name}")
    return 0


def revert_patch() -> int:
    if not TARGET.exists():
        print(f"ERROR: target not found: {TARGET}", file=sys.stderr)
        return 2
    if not is_applied(TARGET.read_text(encoding="utf-8")):
        print("[revert] patch not applied — nothing to revert")
        return 0
    backup = find_backup()
    if backup is None:
        print("ERROR: no backup found to revert from", file=sys.stderr)
        return 7
    shutil.copy2(backup, TARGET)
    print(f"[revert] restored from {backup.name}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--revert", action="store_true", help="restore from backup")
    args = ap.parse_args()
    return revert_patch() if args.revert else apply_patch()


if __name__ == "__main__":
    sys.exit(main())
