"""
Parameterized generator for GH12_click_envvar_flag.

Each seed produces a different CLI tool domain (deploy/backup/migrate) with a
Boolean flag whose envvar branch always evaluates True because the code does
`bool(raw_string)` instead of parsing "false"/"0"/"no" correctly.

Bug: parse_bool_flag() in cli.py calls bool(raw) on the envvar string.
     Any non-empty string is truthy in Python, so DRY_RUN=false → True.
Fix: return raw.lower() not in ("0", "false", "no", "")

Seeds vary: domain, tool name, flag name, envvar name, config target.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom

DOMAIN_CONFIGS = [
    {
        "domain": "deployment",
        "tool_name": "deploytool",
        "command": "deploy",
        "flag_name": "dry_run",
        "flag_long": "--dry-run",
        "envvar": "DEPLOY_DRY_RUN",
        "config_key": "deploy_target",
        "config_values": ["staging", "production", "canary"],
        "action_desc": "deploy the application",
        "dry_desc": "simulate deployment without making changes",
    },
    {
        "domain": "backup",
        "tool_name": "backuptool",
        "command": "backup",
        "flag_name": "dry_run",
        "flag_long": "--dry-run",
        "envvar": "BACKUP_DRY_RUN",
        "config_key": "backup_dest",
        "config_values": ["s3://bucket/backups", "gs://my-backup-bucket", "/mnt/nas/backup"],
        "action_desc": "perform the backup",
        "dry_desc": "simulate backup without writing files",
    },
    {
        "domain": "database migration",
        "tool_name": "migratool",
        "command": "migrate",
        "flag_name": "dry_run",
        "flag_long": "--dry-run",
        "envvar": "MIGRATE_DRY_RUN",
        "config_key": "db_url",
        "config_values": [
            "postgresql://localhost/app",
            "mysql://db-host/schema",
            "sqlite:///app.db",
        ],
        "action_desc": "run database migrations",
        "dry_desc": "show migration plan without applying changes",
    },
]


class Generator(TaskGenerator):
    task_id = "GH12_click_envvar_flag"
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        cfg = DOMAIN_CONFIGS[seed % len(DOMAIN_CONFIGS)]

        config_value = rng.choice(cfg["config_values"])
        default_dry = rng.choice([True, False])

        workspace_files = self._make_workspace(cfg, config_value, default_dry)
        spec_md = self._gen_spec(cfg, config_value, default_dry)
        brief_md = self._gen_brief(cfg)

        return GeneratedTask(
            task_id="GH12_click_envvar_flag",
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "domain": cfg["domain"],
                "tool_name": cfg["tool_name"],
                "flag_name": cfg["flag_name"],
                "envvar": cfg["envvar"],
                "config_value": config_value,
                "default_dry": default_dry,
                "bug": "envvar_string_always_truthy",
                "fix": "parse_bool_flag uses raw.lower() not in ('0','false','no','')",
            },
            workspace_files=workspace_files,
            metadata={"difficulty": "medium", "category": "Real-World GitHub"},
        )

    # ── workspace files ────────────────────────────────────────────────────

    def _make_workspace(self, cfg: dict, config_value: str, default_dry: bool) -> dict:
        return {
            "cli.py": self._gen_cli(cfg, default_dry),
            "config.py": self._gen_config(cfg, config_value),
            "test_cli.py": self._gen_tests(cfg, default_dry),
        }

    def _gen_cli(self, cfg: dict, default_dry: bool) -> str:
        tool = cfg["tool_name"]
        command = cfg["command"]
        flag_name = cfg["flag_name"]
        flag_long = cfg["flag_long"]
        envvar = cfg["envvar"]
        action_desc = cfg["action_desc"]
        dry_desc = cfg["dry_desc"]
        config_key = cfg["config_key"]
        default_str = "True" if default_dry else "False"
        flag_dash = flag_name.replace("_", "-")

        return f'''\
"""
{tool}: CLI tool for {cfg["domain"]}.

The {flag_long} flag controls whether the tool runs in dry-run mode
({dry_desc}).

Flag resolution order (highest to lowest priority):
  1. Explicit CLI flag
  2. Environment variable {envvar}
  3. Default value ({"enabled" if default_dry else "disabled"})
"""
import os
import sys


def parse_bool_flag(flag_value, envvar_name: str, default: bool) -> bool:
    """Resolve a boolean flag from CLI arg, envvar, and default.

    Priority: explicit CLI arg > environment variable > default.

    BUG: the envvar branch uses bool(raw) which is True for ANY non-empty
    string, including "false", "0", "no".  Setting {envvar}=false still
    activates {flag_long} mode.
    """
    if flag_value is not None:
        # Explicit CLI flag always wins
        return bool(flag_value)

    raw = os.environ.get(envvar_name)
    if raw is not None:
        # BUG: any non-empty string is truthy — "false" and "0" become True
        return bool(raw)

    return default


def {command}(dry_run_flag=None):
    """Run the {cfg["domain"]} operation.

    Args:
        dry_run_flag: explicit True/False from CLI, or None if not provided.

    Returns:
        dict with "dry_run" (bool) and "status" (str).
    """
    from config import load_config
    config = load_config()

    dry_run = parse_bool_flag(dry_run_flag, "{envvar}", {default_str})

    if dry_run:
        status = "dry_run: would {action_desc} to {{config['{config_key}']}}"
    else:
        status = "executing: {action_desc} to {{config['{config_key}']}}"

    return {{"dry_run": dry_run, "status": status, "config": config}}


def main():
    import argparse
    parser = argparse.ArgumentParser(description="{tool}")
    sub = parser.add_subparsers(dest="cmd")

    p = sub.add_parser("{command}", help="{action_desc}")
    g = p.add_mutually_exclusive_group()
    g.add_argument("{flag_long}", dest="{flag_name}", action="store_true",
                   default=None, help="{dry_desc} [{envvar}]")
    g.add_argument("--no-{flag_dash}", dest="{flag_name}", action="store_false")
    parser.set_defaults(**{{"{flag_name}": None}})

    args = parser.parse_args()
    if args.cmd == "{command}":
        result = {command}(getattr(args, "{flag_name}"))
        print(result["status"])
        sys.exit(0)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
'''

    def _gen_config(self, cfg: dict, config_value: str) -> str:
        key = cfg["config_key"]
        tool = cfg["tool_name"]
        return f'''\
"""Configuration loader for {tool}."""
import os


DEFAULT_CONFIG = {{
    "{key}": "{config_value}",
    "timeout": 30,
    "retries": 3,
}}


def load_config() -> dict:
    """Load configuration, with optional environment variable overrides."""
    config = dict(DEFAULT_CONFIG)
    env_val = os.environ.get("{key.upper()}")
    if env_val:
        config["{key}"] = env_val
    return config
'''

    def _gen_tests(self, cfg: dict, default_dry: bool) -> str:
        tool = cfg["tool_name"]
        command = cfg["command"]
        flag_name = cfg["flag_name"]
        envvar = cfg["envvar"]
        default_str = "True" if default_dry else "False"

        return f'''\
"""Tests for {tool} boolean flag / envvar interaction.

The core requirement: parse_bool_flag() must correctly interpret envvar
strings.  "false", "0", "no" must yield False; "true", "1", "yes" must
yield True; absent envvar falls back to the default.
"""
import os
import importlib
import pytest


def _clean_env():
    """Remove the test envvar so each test starts clean."""
    os.environ.pop("{envvar}", None)


def _reload():
    import cli as m
    importlib.reload(m)
    return m


def test_envvar_false_string_gives_false():
    """{envvar}=false must produce dry_run=False (core bug)."""
    _clean_env()
    os.environ["{envvar}"] = "false"
    m = _reload()
    result = m.{command}(dry_run_flag=None)
    assert result["dry_run"] is False, (
        f"{envvar}=false produced dry_run={{result['dry_run']}}, expected False"
    )
    _clean_env()


def test_envvar_zero_string_gives_false():
    """{envvar}=0 must produce dry_run=False."""
    _clean_env()
    os.environ["{envvar}"] = "0"
    m = _reload()
    result = m.{command}(dry_run_flag=None)
    assert result["dry_run"] is False, (
        f"{envvar}=0 produced dry_run={{result['dry_run']}}, expected False"
    )
    _clean_env()


def test_envvar_no_string_gives_false():
    """{envvar}=no must produce dry_run=False."""
    _clean_env()
    os.environ["{envvar}"] = "no"
    m = _reload()
    result = m.{command}(dry_run_flag=None)
    assert result["dry_run"] is False, (
        f"{envvar}=no produced dry_run={{result['dry_run']}}, expected False"
    )
    _clean_env()


def test_envvar_true_string_gives_true():
    """{envvar}=true must produce dry_run=True."""
    _clean_env()
    os.environ["{envvar}"] = "true"
    m = _reload()
    result = m.{command}(dry_run_flag=None)
    assert result["dry_run"] is True, (
        f"{envvar}=true produced dry_run={{result['dry_run']}}, expected True"
    )
    _clean_env()


def test_envvar_one_string_gives_true():
    """{envvar}=1 must produce dry_run=True."""
    _clean_env()
    os.environ["{envvar}"] = "1"
    m = _reload()
    result = m.{command}(dry_run_flag=None)
    assert result["dry_run"] is True, (
        f"{envvar}=1 produced dry_run={{result['dry_run']}}, expected True"
    )
    _clean_env()


def test_no_envvar_uses_default():
    """Without envvar, dry_run must equal the hardcoded default ({default_str})."""
    _clean_env()
    m = _reload()
    result = m.{command}(dry_run_flag=None)
    assert result["dry_run"] is {default_str}, (
        f"No envvar produced dry_run={{result['dry_run']}}, expected {default_str}"
    )
    _clean_env()


def test_explicit_true_wins_over_false_envvar():
    """Explicit flag=True overrides {envvar}=false."""
    _clean_env()
    os.environ["{envvar}"] = "false"
    m = _reload()
    result = m.{command}(dry_run_flag=True)
    assert result["dry_run"] is True
    _clean_env()


def test_explicit_false_wins_over_true_envvar():
    """Explicit flag=False overrides {envvar}=true."""
    _clean_env()
    os.environ["{envvar}"] = "true"
    m = _reload()
    result = m.{command}(dry_run_flag=False)
    assert result["dry_run"] is False
    _clean_env()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
'''

    # ── spec / brief ───────────────────────────────────────────────────────

    def _gen_spec(self, cfg: dict, config_value: str, default_dry: bool) -> str:
        tool = cfg["tool_name"]
        command = cfg["command"]
        flag_name = cfg["flag_name"]
        flag_long = cfg["flag_long"]
        envvar = cfg["envvar"]
        default_str = "True" if default_dry else "False"
        flag_dash = flag_name.replace("_", "-")

        return f"""\
# GH12: Envvar Boolean Flag Always True — Full Specification (Planner Only)

## Overview

The workspace implements `{tool}`, a CLI tool for {cfg["domain"]}. It has a
`{flag_long}` flag that can also be controlled via the `{envvar}` environment
variable. There is **one bug** in `cli.py`.

## Program Structure

- `cli.py` — CLI tool with the buggy `parse_bool_flag()` function
- `config.py` — configuration loader (correct, do not modify)
- `test_cli.py` — pytest tests that detect the bug

## The Bug

**Location:** `parse_bool_flag()` in `cli.py`, the environment-variable branch.

**Root cause:** The code uses `bool(raw)` to convert the envvar string to a
boolean. In Python, `bool(s)` is `True` for any non-empty string, so
`bool("false")`, `bool("0")`, and `bool("no")` all return `True`.

This means `{envvar}=false` still activates `{flag_long}` mode.

**Buggy code:**
```python
raw = os.environ.get(envvar_name)
if raw is not None:
    return bool(raw)   # always True for non-empty string
```

**Fix:**
```python
raw = os.environ.get(envvar_name)
if raw is not None:
    return raw.lower() not in ("0", "false", "no", "")
```

## Flag Resolution (after fix)

| Source | Value | Result |
|--------|-------|--------|
| CLI arg | `{flag_long}` | `True` |
| CLI arg | `--no-{flag_dash}` | `False` |
| Envvar | `true`, `1`, `yes` | `True` |
| Envvar | `false`, `0`, `no` | `False` |
| None | — | `{default_str}` (default) |

## Acceptance Criteria

1. `{envvar}=false` → `dry_run = False`
2. `{envvar}=0` → `dry_run = False`
3. `{envvar}=no` → `dry_run = False`
4. `{envvar}=true` → `dry_run = True`
5. `{envvar}=1` → `dry_run = True`
6. No envvar → `dry_run = {default_str}` (default)
7. Explicit CLI arg always overrides envvar
8. All tests pass: `pytest test_cli.py -v`

## Important Notes

- Only `parse_bool_flag()` in `cli.py` needs changing (~1-2 lines)
- Do NOT modify `config.py` or `test_cli.py`
"""

    def _gen_brief(self, cfg: dict) -> str:
        tool = cfg["tool_name"]
        flag_long = cfg["flag_long"]
        envvar = cfg["envvar"]

        return f"""\
# GH12: CLI Flag Envvar Bug (Brief)

Fix `{tool}` so the `{flag_long}` flag correctly respects the `{envvar}`
environment variable.

Currently, `{envvar}=false` still activates dry-run mode. After your fix,
setting the envvar to `false`, `0`, or `no` must disable the flag.

Verify with:
```
pytest test_cli.py -v
```

**Files to fix:** `cli.py`
**Do NOT modify:** `config.py` or `test_cli.py`

Follow the Planner's guidance precisely.
"""
