"""
Parameterized generator for GH14_celery_chain_fail.

Each seed produces a different data-processing pipeline domain
(ETL/image-resize/report-generation) with a chain of groups where the first
group's failure is silently swallowed.

Bug: Celery converts groups inside a chain into chords internally.  The
     chord callback's error propagation only works for the *terminal* chord;
     intermediate chord failures do not propagate to the final result unless
     each group is explicitly wrapped with link_error or the pipeline is
     restructured with explicit error callbacks.

     In the simplified standalone reproduction, the bug is modelled without
     real Celery: pipeline.py has a chain executor where intermediate stage
     failures are swallowed because the continuation ignores exception state
     when iterating results.

Fix: check each stage result for errors before continuing; raise/propagate
     the error so the final result reflects the failure.

Seeds vary: domain, stage names, task names, error trigger value.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom

DOMAIN_CONFIGS = [
    {
        "domain": "ETL pipeline",
        "pipeline_name": "EtlPipeline",
        "stage1_name": "extract",
        "stage2_name": "transform",
        "stage3_name": "load",
        "item_name": "record",
        "item_plural": "records",
        "error_item": "POISON_PILL",
        "stage1_desc": "extract records from source",
        "stage2_desc": "transform each record",
        "stage3_desc": "load records into destination",
    },
    {
        "domain": "image processing pipeline",
        "pipeline_name": "ImagePipeline",
        "stage1_name": "decode",
        "stage2_name": "resize",
        "stage3_name": "encode",
        "item_name": "image",
        "item_plural": "images",
        "error_item": "CORRUPT_IMAGE",
        "stage1_desc": "decode raw image bytes",
        "stage2_desc": "resize each decoded image",
        "stage3_desc": "encode resized images for output",
    },
    {
        "domain": "report generation pipeline",
        "pipeline_name": "ReportPipeline",
        "stage1_name": "collect",
        "stage2_name": "aggregate",
        "stage3_name": "render",
        "item_name": "data_point",
        "item_plural": "data points",
        "error_item": "INVALID_DATA",
        "stage1_desc": "collect data points from sources",
        "stage2_desc": "aggregate collected data",
        "stage3_desc": "render aggregated data into report",
    },
]


class Generator(TaskGenerator):
    task_id = "GH14_celery_chain_fail"
    domain = "Real-World GitHub"
    difficulty = "hard"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        cfg = DOMAIN_CONFIGS[seed % len(DOMAIN_CONFIGS)]
        num_items = rng.randint(4, 8)
        error_position = rng.randint(0, num_items - 1)

        workspace_files = self._make_workspace(cfg, num_items, error_position)
        spec_md = self._gen_spec(cfg, num_items, error_position)
        brief_md = self._gen_brief(cfg)

        return GeneratedTask(
            task_id="GH14_celery_chain_fail",
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "domain": cfg["domain"],
                "pipeline_name": cfg["pipeline_name"],
                "num_items": num_items,
                "error_position": error_position,
                "error_item": cfg["error_item"],
                "bug": "intermediate_stage_failure_silently_swallowed",
                "fix": "check stage results for errors before continuing chain",
            },
            workspace_files=workspace_files,
            metadata={"difficulty": "hard", "category": "Real-World GitHub"},
        )

    # ── workspace files ────────────────────────────────────────────────────

    def _make_workspace(self, cfg: dict, num_items: int, error_position: int) -> dict:
        return {
            "pipeline.py": self._gen_pipeline(cfg, num_items, error_position),
            "tasks.py": self._gen_tasks(cfg),
            "test_pipeline.py": self._gen_tests(cfg, num_items, error_position),
        }

    def _gen_tasks(self, cfg: dict) -> str:
        s1 = cfg["stage1_name"]
        s2 = cfg["stage2_name"]
        s3 = cfg["stage3_name"]
        item = cfg["item_name"]
        error_item = cfg["error_item"]
        d1 = cfg["stage1_desc"]
        d2 = cfg["stage2_desc"]
        d3 = cfg["stage3_desc"]

        return f'''\
"""
Individual stage tasks for the {cfg["domain"]}.

Each task processes one item and either returns a result dict or raises
ValueError if the item is the designated error trigger ({error_item!r}).
"""


class StageError(Exception):
    """Raised when a stage task fails to process an item."""
    pass


def {s1}_item(item: str) -> dict:
    """{d1.capitalize()}.

    Raises StageError if item == {error_item!r}.
    """
    if item == "{error_item}":
        raise StageError(f"Stage '{s1}' failed: invalid item {{item!r}}")
    return {{"stage": "{s1}", "item": item, "status": "ok"}}


def {s2}_item(result: dict) -> dict:
    """{d2.capitalize()}.

    Raises StageError if upstream result indicates failure.
    """
    if result.get("status") == "error":
        raise StageError(f"Stage '{s2}' received failed upstream result: {{result}}")
    return {{"stage": "{s2}", "item": result["item"], "status": "ok"}}


def {s3}_item(result: dict) -> dict:
    """{d3.capitalize()}.

    Raises StageError if upstream result indicates failure.
    """
    if result.get("status") == "error":
        raise StageError(f"Stage '{s3}' received failed upstream result: {{result}}")
    return {{"stage": "{s3}", "item": result["item"], "status": "ok"}}
'''

    def _gen_pipeline(self, cfg: dict, num_items: int, error_position: int) -> str:
        s1 = cfg["stage1_name"]
        s2 = cfg["stage2_name"]
        s3 = cfg["stage3_name"]
        pipeline_name = cfg["pipeline_name"]
        item_plural = cfg["item_plural"]
        error_item = cfg["error_item"]
        domain = cfg["domain"]

        return f'''\
"""
{domain} — chained group executor.

Simulates Celery's chain-of-groups pattern WITHOUT requiring a running broker.
Each "group" is a list of tasks applied to each item; the groups are chained
so the output of stage N becomes the input to stage N+1.

BUG: When a stage-1 task raises an exception, the executor catches it and
stores a sentinel error dict, but the continuation loop does NOT check for
error dicts before passing results to the next stage.  Stage-2 and stage-3
then happily process the error sentinel, and the final result appears
successful even though stage-1 failed.

This mirrors Celery's behaviour where intermediate chord failures are not
propagated to the final chord callback.
"""
from tasks import {s1}_item, {s2}_item, {s3}_item, StageError


def _run_group(fn, items):
    """Apply fn to each item in the group, catching exceptions.

    BUG: exceptions are swallowed into an error dict instead of being
    propagated.  The caller does not inspect these error dicts.
    """
    results = []
    for item in items:
        try:
            results.append(fn(item))
        except Exception as exc:
            # BUG: silently convert exception to an error dict and continue
            results.append({{"status": "error", "reason": str(exc), "item": item}})
    return results


def _chain_groups(items):
    """Execute the three-stage chain.

    BUG: each _run_group call passes results unconditionally to the next
    stage.  Error dicts from stage 1 flow into stage 2 and stage 3 without
    raising, so the overall result looks like success.
    """
    stage1_results = _run_group({s1}_item, items)
    # BUG: no check here — error dicts pass silently to stage 2
    stage2_results = _run_group({s2}_item, stage1_results)
    # BUG: no check here — error dicts pass silently to stage 3
    stage3_results = _run_group({s3}_item, stage2_results)
    return stage3_results


class {pipeline_name}:
    """Run the {domain} chain for a list of {item_plural}."""

    def run(self, items: list[str]) -> list[dict]:
        """Execute the pipeline and return final results.

        Should raise StageError if any item fails in any stage.
        Currently swallows failures silently (the bug).
        """
        return _chain_groups(items)
'''

    def _gen_tests(self, cfg: dict, num_items: int, error_position: int) -> str:
        pipeline_name = cfg["pipeline_name"]
        s1 = cfg["stage1_name"]
        error_item = cfg["error_item"]
        item_plural = cfg["item_plural"]
        domain = cfg["domain"]

        # Build a representative item list with the error item at error_position
        items_repr = ", ".join(
            f'"{error_item}"' if i == error_position else f'"item_{i}"'
            for i in range(num_items)
        )

        return f'''\
"""
Tests for {domain} error propagation.

The critical requirement: if any item in stage 1 raises StageError, the
pipeline must propagate that error rather than silently continuing.
"""
import pytest
from pipeline import {pipeline_name}
from tasks import StageError


GOOD_ITEMS = [{", ".join(f'"item_{i}"' for i in range(num_items))}]
BAD_ITEMS  = [{items_repr}]


def test_success_path_returns_all_results():
    """Pipeline with no errors must return {num_items} successful results."""
    pipeline = {pipeline_name}()
    results = pipeline.run(GOOD_ITEMS)
    assert len(results) == {num_items}, (
        f"Expected {num_items} results, got {{len(results)}}"
    )
    for r in results:
        assert r.get("status") == "ok", f"Unexpected result: {{r}}"


def test_stage1_failure_propagates():
    """A stage-1 failure must raise StageError, not return silently."""
    pipeline = {pipeline_name}()
    with pytest.raises((StageError, Exception)) as exc_info:
        pipeline.run(BAD_ITEMS)
    # Ensure it's actually a failure signal, not a false positive
    assert exc_info.value is not None, "Expected an exception to propagate"


def test_stage1_failure_not_swallowed():
    """Pipeline must NOT return a list of dicts when stage 1 fails."""
    pipeline = {pipeline_name}()
    try:
        result = pipeline.run(BAD_ITEMS)
        # If we reach here, the bug is present — check that at least one
        # result reflects the error
        error_results = [r for r in result if r.get("status") == "error"]
        assert error_results, (
            "Pipeline returned success results despite stage-1 failure — "
            "error was silently swallowed"
        )
        # If there are error results, the pipeline should have raised instead
        pytest.fail(
            f"Pipeline returned {{len(error_results)}} error dict(s) instead of "
            f"raising — failures must propagate as exceptions"
        )
    except (StageError, Exception):
        pass  # Correct behaviour: exception propagated


def test_error_position_is_detected():
    """The item at position {error_position} ({error_item!r}) must cause failure."""
    pipeline = {pipeline_name}()
    single_bad = ["{error_item}"]
    with pytest.raises((StageError, Exception)):
        pipeline.run(single_bad)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
'''

    # ── spec / brief ───────────────────────────────────────────────────────

    def _gen_spec(self, cfg: dict, num_items: int, error_position: int) -> str:
        pipeline_name = cfg["pipeline_name"]
        s1 = cfg["stage1_name"]
        s2 = cfg["stage2_name"]
        s3 = cfg["stage3_name"]
        error_item = cfg["error_item"]
        domain = cfg["domain"]

        return f"""\
# GH14: Chain-of-Groups Failure Propagation — Full Specification (Planner Only)

## Overview

The workspace implements a {domain} (`{pipeline_name}`) that chains three
stages: `{s1}` → `{s2}` → `{s3}`. There is **one bug** in `pipeline.py`
where failures in stage 1 are silently swallowed.

## Program Structure

- `pipeline.py` — chain executor with the bug (`_run_group`, `_chain_groups`)
- `tasks.py` — individual stage functions (correct, do not modify)
- `test_pipeline.py` — pytest tests that detect the bug

## The Bug

**Location:** `_run_group()` and `_chain_groups()` in `pipeline.py`.

**Root cause:** This mirrors Celery's chain-of-groups behaviour.  When Celery
converts a `group | chain` into chords internally, failures in an intermediate
chord's tasks do not automatically propagate to subsequent chords' callbacks.
The `on_error` / `link_error` mechanism must be wired explicitly.

In this standalone reproduction, `_run_group()` catches exceptions and stores
error sentinel dicts instead of re-raising.  `_chain_groups()` passes the
results unconditionally to the next stage — so a `{error_item!r}` item in
stage 1 produces an error dict that flows silently through stage 2 and 3.

**Buggy code:**
```python
def _chain_groups(items):
    stage1_results = _run_group({s1}_item, items)
    # BUG: no check — error dicts pass to stage 2
    stage2_results = _run_group({s2}_item, stage1_results)
    stage3_results = _run_group({s3}_item, stage2_results)
    return stage3_results
```

**Fix:** After each `_run_group` call, inspect results for error dicts and
raise if any are found:
```python
def _check_results(results, stage_name):
    errors = [r for r in results if r.get("status") == "error"]
    if errors:
        reasons = "; ".join(r.get("reason", "unknown") for r in errors)
        raise StageError(f"Stage '{{stage_name}}' had {{len(errors)}} failure(s): {{reasons}}")

def _chain_groups(items):
    stage1_results = _run_group({s1}_item, items)
    _check_results(stage1_results, "{s1}")
    stage2_results = _run_group({s2}_item, stage1_results)
    _check_results(stage2_results, "{s2}")
    stage3_results = _run_group({s3}_item, stage2_results)
    _check_results(stage3_results, "{s3}")
    return stage3_results
```

## Acceptance Criteria

1. `pipeline.run(["{error_item}"])` raises `StageError` (or subclass)
2. `pipeline.run(["{error_item}", "item_1"])` raises `StageError`
3. `pipeline.run(["item_0", "item_1", ...])` (no error item) returns all-ok results
4. All tests pass: `pytest test_pipeline.py -v`

## Important Notes

- Fix is in `pipeline.py` only — `_run_group` and/or `_chain_groups`
- Do NOT modify `tasks.py` or `test_pipeline.py`
"""

    def _gen_brief(self, cfg: dict) -> str:
        pipeline_name = cfg["pipeline_name"]
        domain = cfg["domain"]
        s1 = cfg["stage1_name"]
        error_item = cfg["error_item"]

        return f"""\
# GH14: Pipeline Failure Propagation (Brief)

Fix the {domain} (`{pipeline_name}`) so failures in any stage propagate
correctly rather than being silently swallowed.

Currently, a bad item (`{error_item!r}`) in stage `{s1}` causes no visible
error — the pipeline returns as if it succeeded.

Verify with:
```
pytest test_pipeline.py -v
```

**Files to fix:** `pipeline.py`
**Do NOT modify:** `tasks.py` or `test_pipeline.py`

Follow the Planner's guidance precisely.
"""
