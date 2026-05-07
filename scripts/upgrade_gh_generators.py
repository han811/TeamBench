"""
Upgrade script for GH generator deep parameterization.

Reads each generators/gen_gh*.py, detects the current simple parameterization
pattern, and generates an upgraded version that calls gh_deep_param functions
AFTER the existing code (preserving backward compatibility).

Usage:
    python scripts/upgrade_gh_generators.py [--dry-run] [--limit N] [--output-dir DIR]

Options:
    --dry-run       Print what would be changed without writing files
    --limit N       Only process first N generators (for testing)
    --output-dir    Write upgraded files here instead of overwriting originals
                    (default: overwrite in-place)
    --report        Print a summary report at the end

Safety:
    - Only modifies the generate() method
    - Preserves all existing logic exactly as-is
    - Adds deep parameterization calls AFTER the existing suffix rename
    - Does NOT touch _base_workspace() or any other methods
    - Creates a .bak backup before overwriting (unless --no-backup)
"""
from __future__ import annotations

import argparse
import ast
import os
import re
import sys
import shutil
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Detection patterns
# ---------------------------------------------------------------------------

# The canonical simple-rename pattern we're looking for
_SIMPLE_RENAME_PATTERN = re.compile(
    r"""
    (?P<indent>[ \t]*)                        # leading indentation
    \#\s*Apply\s+seed[-\s]based\s+renaming.*\n  # comment line
    (?P<body>                                  # capture the whole block
        (?:[ \t]+.*\n)*                       # all lines until end of block
    )
    """,
    re.VERBOSE,
)

# Simpler pattern: detect if generate() already uses gh_deep_param
_ALREADY_UPGRADED_PATTERN = re.compile(r'gh_deep_param|deep_rename_symbols|add_realistic_noise')

# Pattern to find the return statement in generate()
_RETURN_PATTERN = re.compile(r'^([ \t]*)return\s+GeneratedTask\(', re.MULTILINE)


# ---------------------------------------------------------------------------
# The upgrade injection template
# ---------------------------------------------------------------------------

_UPGRADE_INJECTION = """\
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
"""


# ---------------------------------------------------------------------------
# Upgrade logic
# ---------------------------------------------------------------------------

def detect_upgrade_site(source: str) -> Optional[int]:
    """
    Find the insertion point for the deep parameterization block.
    Returns the character offset of the line just before `return GeneratedTask(`.

    We insert AFTER the existing simple-rename block and BEFORE the return.
    Returns None if we can't safely find the insertion point.
    """
    # Verify the generate() method exists
    if "def generate(self, seed: int) -> GeneratedTask:" not in source:
        return None

    # Find all return GeneratedTask( occurrences — should be exactly one
    matches = list(_RETURN_PATTERN.finditer(source))
    if len(matches) != 1:
        return None

    return_match = matches[0]
    return_offset = return_match.start()

    # The insertion point is the start of the return line
    return return_offset


def build_upgraded_source(source: str) -> Optional[str]:
    """
    Build the upgraded generator source by injecting deep parameterization
    calls just before the `return GeneratedTask(` statement.

    Returns None if the source:
    - Already uses gh_deep_param
    - Doesn't have the expected simple-rename pattern
    - Can't be safely modified
    """
    # Skip already-upgraded files
    if _ALREADY_UPGRADED_PATTERN.search(source):
        return None

    # Find insertion point
    insert_at = detect_upgrade_site(source)
    if insert_at is None:
        return None

    # Check the simple rename pattern exists (to confirm this is a GH generator)
    if 'suffixes = ["", "_alt", "_impl"]' not in source:
        return None

    # Inject before the return statement
    upgraded = source[:insert_at] + _UPGRADE_INJECTION + source[insert_at:]

    # Validate the result parses as valid Python
    try:
        ast.parse(upgraded)
    except SyntaxError as e:
        return None  # Don't produce broken code

    return upgraded


# ---------------------------------------------------------------------------
# Report helpers
# ---------------------------------------------------------------------------

class UpgradeReport:
    def __init__(self):
        self.upgraded: list[str] = []
        self.skipped_already_upgraded: list[str] = []
        self.skipped_no_pattern: list[str] = []
        self.skipped_syntax_error: list[str] = []
        self.errors: list[tuple[str, str]] = []

    def summary(self) -> str:
        lines = [
            f"\n{'='*60}",
            f"GH Generator Upgrade Report",
            f"{'='*60}",
            f"  Upgraded:                {len(self.upgraded)}",
            f"  Already upgraded:        {len(self.skipped_already_upgraded)}",
            f"  Skipped (no pattern):    {len(self.skipped_no_pattern)}",
            f"  Skipped (syntax error):  {len(self.skipped_syntax_error)}",
            f"  Errors:                  {len(self.errors)}",
            f"{'='*60}",
        ]
        if self.errors:
            lines.append("\nErrors:")
            for path, err in self.errors[:10]:
                lines.append(f"  {path}: {err}")
        if self.skipped_syntax_error:
            lines.append("\nSyntax errors after upgrade (first 5):")
            for path in self.skipped_syntax_error[:5]:
                lines.append(f"  {path}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Upgrade GH generators with deep parameterization."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print changes without writing files",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Only process first N generators (for testing)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Write upgraded files to this directory instead of in-place",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip creating .bak backup files before overwriting",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Print summary report at the end",
    )
    args = parser.parse_args()

    # Resolve paths
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent
    gen_dir = repo_root / "generators"

    if args.output_dir:
        out_dir = Path(args.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
    else:
        out_dir = None

    # Collect generators
    gen_files = sorted(
        p for p in gen_dir.iterdir()
        if p.name.startswith("gen_gh") and p.suffix == ".py"
    )

    if args.limit:
        gen_files = gen_files[: args.limit]

    report = UpgradeReport()

    for gen_path in gen_files:
        try:
            source = gen_path.read_text(encoding="utf-8")
        except Exception as e:
            report.errors.append((gen_path.name, f"read error: {e}"))
            continue

        upgraded = build_upgraded_source(source)

        if upgraded is None:
            if _ALREADY_UPGRADED_PATTERN.search(source):
                report.skipped_already_upgraded.append(gen_path.name)
                if args.dry_run:
                    print(f"[SKIP-UPGRADED] {gen_path.name}")
            elif 'suffixes = ["", "_alt", "_impl"]' not in source:
                report.skipped_no_pattern.append(gen_path.name)
                if args.dry_run:
                    print(f"[SKIP-NO-PATTERN] {gen_path.name}")
            else:
                report.skipped_syntax_error.append(gen_path.name)
                if args.dry_run:
                    print(f"[SKIP-SYNTAX] {gen_path.name}")
            continue

        report.upgraded.append(gen_path.name)

        if args.dry_run:
            print(f"[UPGRADE] {gen_path.name}")
            # Show the diff context
            lines = source.splitlines()
            upgraded_lines = upgraded.splitlines()
            added = set(upgraded_lines) - set(lines)
            for line in added:
                if line.strip():
                    print(f"  + {line.rstrip()}")
            continue

        # Write the upgraded file
        if out_dir:
            dest_path = out_dir / gen_path.name
        else:
            dest_path = gen_path
            # Create backup
            if not args.no_backup:
                bak_path = gen_path.with_suffix(".py.bak")
                shutil.copy2(gen_path, bak_path)

        dest_path.write_text(upgraded, encoding="utf-8")
        print(f"[UPGRADED] {gen_path.name} -> {dest_path}")

    if args.report or args.dry_run:
        print(report.summary())

    return 0


if __name__ == "__main__":
    sys.exit(main())
