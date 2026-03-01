"""
Parameterized generator for TRAP2: False Fix.

Each seed produces a data-processing library with:
  - 5 genuine bugs (Issues 1-5) that must be fixed
  - 3 intentional design choices (Issues 6-8) that must NOT be changed

Seed variation: function/field/class names change across seeds so agents
cannot memoise a single solution.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom


# ── Seed-indexed name pools ────────────────────────────────────────────────
# Each index corresponds to one seed group (seed % N).

# Class / module theme names
THEMES = ["order", "event", "record", "entry", "item"]

# Field names used in the data records
TS_FIELDS   = ["timestamp", "created_at", "event_time", "recorded_at", "ts"]
ID_FIELDS   = ["id", "record_id", "event_id", "entry_id", "item_id"]
VAL_FIELDS  = ["value", "amount", "score", "weight", "count"]

# Processor class names
PROC_NAMES  = ["DataProcessor", "RecordProcessor", "EventProcessor",
               "EntryProcessor", "ItemProcessor"]

# Cache class names
CACHE_NAMES = ["DataCache", "RecordCache", "EventCache",
               "EntryCache", "ItemCache"]

# Sorter class names
SORTER_NAMES = ["Sorter", "RecordSorter", "EventSorter",
                "EntrySorter", "ItemSorter"]

# Reader class names
READER_NAMES = ["BatchReader", "RecordReader", "EventReader",
                "EntryReader", "ItemReader"]

# BatchProcessor class names (wraps reader)
BATCH_NAMES  = ["BatchProcessor", "RecordBatcher", "EventBatcher",
                "EntryBatcher", "ItemBatcher"]

# Filenames for the load_data() source file (seed-parameterised)
DATA_FILENAMES = ["orders.csv", "events.csv", "records.csv",
                  "entries.csv", "items.csv"]


class Generator(TaskGenerator):
    task_id  = "TRAP2_false_fix"
    domain   = "SWE"
    difficulty = "expert"
    languages  = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        idx = seed % len(THEMES)

        # Pick names for this seed
        theme      = THEMES[idx]
        ts_field   = TS_FIELDS[idx]
        id_field   = ID_FIELDS[idx]
        val_field  = VAL_FIELDS[idx]
        proc_cls   = PROC_NAMES[idx]
        cache_cls  = CACHE_NAMES[idx]
        sorter_cls = SORTER_NAMES[idx]
        reader_cls = READER_NAMES[idx]
        batch_cls  = BATCH_NAMES[idx]
        data_file  = DATA_FILENAMES[idx]

        names = dict(
            theme=theme, ts_field=ts_field, id_field=id_field,
            val_field=val_field, proc_cls=proc_cls, cache_cls=cache_cls,
            sorter_cls=sorter_cls, reader_cls=reader_cls,
            batch_cls=batch_cls, data_file=data_file,
        )

        workspace_files = self._make_workspace(names)

        tasks_dir = os.path.join(os.path.dirname(__file__), "..", "tasks", "TRAP2_false_fix")
        with open(os.path.join(tasks_dir, "spec.md")) as f:
            spec_md = f.read()
        with open(os.path.join(tasks_dir, "brief.md")) as f:
            brief_md = f.read()

        return GeneratedTask(
            task_id="TRAP2_false_fix",
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "genuine_bugs": ["I1", "I2", "I3", "I4", "I5"],
                "false_issues": ["I6", "I7", "I8"],
                "seed": seed,
                "ts_field": ts_field,
                "proc_cls": proc_cls,
            },
            workspace_files=workspace_files,
            metadata={"difficulty": "expert", "category": "SWE"},
        )

    # ── Workspace construction ─────────────────────────────────────────────

    def _make_workspace(self, n: dict) -> dict:
        files: dict[str, str] = {}

        files["lib/__init__.py"] = (
            f"from lib.processor import {n['proc_cls']}\n"
            f"from lib.cache import {n['cache_cls']}\n"
            f"from lib.sorter import {n['sorter_cls']}\n"
            f"from lib.reader import {n['reader_cls']}, {n['batch_cls']}\n"
        )

        files["lib/processor.py"]      = self._processor(n)
        files["lib/cache.py"]          = self._cache(n)
        files["lib/sorter.py"]         = self._sorter(n)
        files["lib/reader.py"]         = self._reader(n)
        files["tests/__init__.py"]     = ""
        files["tests/test_processor.py"] = self._test_processor(n)
        files["tests/test_cache.py"]   = self._test_cache(n)
        files["tests/test_sorter.py"]  = self._test_sorter(n)
        files["tests/test_reader.py"]  = self._test_reader(n)
        files["tests/test_integration.py"] = self._test_integration(n)
        files["BUG_REPORT.md"]         = self._bug_report(n)
        files["ARCHITECTURE.md"]       = self._architecture(n)
        files["requirements.txt"]      = "pytest\n"

        return files

    # ── lib/processor.py  (Issues 1, 2, 3 — all buggy) ───────────────────

    def _processor(self, n: dict) -> str:
        tf = n["ts_field"]
        idf = n["id_field"]
        vf = n["val_field"]
        cls = n["proc_cls"]
        return f'''\
"""Data processor — seed-parameterised."""
from typing import List, Dict, Any


class {cls}:
    """Processes and paginates data records."""

    def process(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Sort records by {tf} (descending) and return them.

        Issue 2 (genuine): crashes if records is empty.
        Issue 3 (genuine): sorts ascending instead of descending.
        """
        # BUG 2: no guard for empty list — records[0] below would IndexError
        _ = records[0]  # sentinel access to trigger the bug on empty input

        # BUG 3: should be reverse=True (descending by {tf})
        return sorted(records, key=lambda r: r["{tf}"])

    def paginate(
        self,
        records: List[Dict[str, Any]],
        page: int,
        page_size: int,
    ) -> List[Dict[str, Any]]:
        """Return the records for the given 1-based page number.

        Issue 1 (genuine): off-by-one — uses page * page_size as start
        instead of (page - 1) * page_size.
        """
        # BUG 1: should be (page - 1) * page_size
        start = page * page_size
        end   = start + page_size
        return records[start:end]
'''

    # ── lib/cache.py  (Issue 6 — intentional double invalidation) ────────

    def _cache(self, n: dict) -> str:
        cls = n["cache_cls"]
        return f'''\
"""Cache with concurrent-write safety."""
from typing import Any, Dict


class {cls}:
    """In-memory cache with an index for fast lookups.

    Design note: invalidate_on_write() calls both clear() and
    rebuild_index(). BUG_REPORT calls this "redundant double
    invalidation", but ARCHITECTURE.md explains why both calls are
    required for concurrent-write safety.
    """

    def __init__(self) -> None:
        self._store: Dict[str, Any] = {{}}
        self._index: Dict[str, str] = {{}}

    def get(self, key: str) -> Any:
        return self._store.get(key)

    def put(self, key: str, value: Any) -> None:
        self._store[key] = value
        self._index[key] = str(value)

    def clear(self) -> None:
        self._store.clear()

    def rebuild_index(self) -> None:
        """Rebuild the lookup index from current store contents."""
        self._index = {{k: str(v) for k, v in self._store.items()}}

    def invalidate_on_write(self) -> None:
        """Invalidate cache on external write.

        INTENTIONAL: both clear() and rebuild_index() are called.
        clear() removes stale data; rebuild_index() then resets
        the index so it is consistent with the (now empty) store.
        Removing either call causes stale index entries in concurrent
        write scenarios. See ARCHITECTURE.md §Cache.
        """
        self.clear()
        self.rebuild_index()
'''

    # ── lib/sorter.py  (Issues 4, 5 buggy; Issue 7 intentional O(n²)) ───

    def _sorter(self, n: dict) -> str:
        cls  = n["sorter_cls"]
        tf   = n["ts_field"]
        dfile = n["data_file"]
        return f'''\
"""Sorter with stable ordering guarantee."""
from datetime import datetime
from typing import Any, Dict, List


class {cls}:
    """Sorts records by date with a stability guarantee.

    stable_sort() uses insertion sort intentionally — see ARCHITECTURE.md §Sorter.
    """

    def parse_date(self, date_str: str) -> datetime:
        """Parse a date string.

        Issue 4 (genuine): format is %d/%m/%Y but data uses %Y-%m-%d.
        """
        # BUG 4: wrong format — should be "%Y-%m-%d"
        return datetime.strptime(date_str, "%d/%m/%Y")

    def load_data(self, filepath: str) -> List[str]:
        """Load lines from a file.

        Issue 5 (genuine): file handle is never closed.
        """
        # BUG 5: missing close() / no context manager
        f = open(filepath, "r")
        lines = f.readlines()
        return [line.strip() for line in lines]

    def stable_sort(
        self, records: List[Dict[str, Any]], key: str = "{tf}"
    ) -> List[Dict[str, Any]]:
        """Sort records using insertion sort.

        INTENTIONAL (Issue 7): insertion sort is O(n²) but guarantees
        stable, deterministic ordering. See ARCHITECTURE.md §Sorter.
        Do NOT replace with sorted() or list.sort().
        """
        result = list(records)
        for i in range(1, len(result)):
            current = result[i]
            j = i - 1
            while j >= 0 and result[j][key] > current[key]:
                result[j + 1] = result[j]
                j -= 1
            result[j + 1] = current
        return result
'''

    # ── lib/reader.py  (Issue 8 — intentional no try/except) ─────────────

    def _reader(self, n: dict) -> str:
        reader_cls = n["reader_cls"]
        batch_cls  = n["batch_cls"]
        return f'''\
"""Batch reader with deliberate exception propagation."""
from typing import Any, Dict, List


class {reader_cls}:
    """Reads and parses raw data batches.

    Design note: parse_batch() has no try/except intentionally.
    See ARCHITECTURE.md §Reader.
    """

    def parse_batch(self, raw: List[str]) -> List[Dict[str, Any]]:
        """Parse a list of raw strings into record dicts.

        INTENTIONAL (Issue 8): no try/except here. Exceptions propagate
        to {batch_cls}.run() which wraps them with context. Adding a
        handler here would swallow errors silently. See ARCHITECTURE.md.
        """
        records = []
        for line in raw:
            parts = line.split(",")
            record = {{
                "id":    parts[0].strip(),
                "value": float(parts[1].strip()),
                "ts":    int(parts[2].strip()),
            }}
            records.append(record)
        return records


class {batch_cls}:
    """Orchestrates batch reading with error context."""

    def __init__(self, reader: {reader_cls}) -> None:
        self._reader = reader

    def run(self, batches: List[List[str]]) -> List[Dict[str, Any]]:
        """Process all batches, wrapping parse errors with context."""
        results: List[Dict[str, Any]] = []
        for i, batch in enumerate(batches):
            try:
                results.extend(self._reader.parse_batch(batch))
            except (ValueError, IndexError) as exc:
                raise RuntimeError(
                    f"Batch {{i}} failed to parse: {{exc}}"
                ) from exc
        return results
'''

    # ── Tests ─────────────────────────────────────────────────────────────

    def _test_processor(self, n: dict) -> str:
        cls = n["proc_cls"]
        tf  = n["ts_field"]
        return f'''\
"""Tests for {cls} — issues 1, 2, 3."""
import pytest
from lib.processor import {cls}


@pytest.fixture
def proc():
    return {cls}()


def _rec(ts):
    return {{"id": ts, "{tf}": ts, "value": ts * 10}}


def test_process_sort_order(proc):
    """Issue 3: process() must sort descending by {tf}."""
    records = [_rec(3), _rec(1), _rec(5), _rec(2)]
    result = proc.process(records)
    ts_vals = [r["{tf}"] for r in result]
    assert ts_vals == sorted(ts_vals, reverse=True), (
        f"Expected descending order, got {{ts_vals}}"
    )


def test_process_empty_input(proc):
    """Issue 2: process() must not crash on empty list."""
    result = proc.process([])
    assert result == []


def test_paginate_page1(proc):
    """Issue 1: page=1 must return first page_size items."""
    records = [_rec(i) for i in range(10)]
    page1 = proc.paginate(records, page=1, page_size=3)
    assert page1 == records[0:3], f"page=1 got {{page1}}"


def test_paginate_page2(proc):
    """Issue 1: page=2 must return second page_size items."""
    records = [_rec(i) for i in range(10)]
    page2 = proc.paginate(records, page=2, page_size=3)
    assert page2 == records[3:6], f"page=2 got {{page2}}"
'''

    def _test_cache(self, n: dict) -> str:
        cls = n["cache_cls"]
        return f'''\
"""Tests for {cls} — verify double invalidation is preserved (Issue 6)."""
import pytest
from lib.cache import {cls}


@pytest.fixture
def cache():
    c = {cls}()
    c.put("k1", "v1")
    c.put("k2", "v2")
    return c


def test_get_put(cache):
    assert cache.get("k1") == "v1"


def test_invalidate_clears_store(cache):
    """After invalidate_on_write(), store must be empty."""
    cache.invalidate_on_write()
    assert cache.get("k1") is None
    assert cache.get("k2") is None


def test_invalidate_resets_index(cache):
    """After invalidate_on_write(), index must be consistent with empty store.

    This test BREAKS if rebuild_index() is removed from invalidate_on_write().
    The index must be empty after the store is cleared, otherwise stale
    entries remain — the exact concurrent-safety bug described in ARCHITECTURE.
    """
    cache.invalidate_on_write()
    # Rebuilding after clear must produce an empty index
    assert cache._index == {{}}, (
        "Index is not empty after invalidation — stale entries present"
    )


def test_invalidate_then_put(cache):
    """New items after invalidation must be retrievable."""
    cache.invalidate_on_write()
    cache.put("new_key", "new_val")
    assert cache.get("new_key") == "new_val"
'''

    def _test_sorter(self, n: dict) -> str:
        cls  = n["sorter_cls"]
        tf   = n["ts_field"]
        return f'''\
"""Tests for {cls} — issues 4, 5; stable sort must remain insertion sort (Issue 7)."""
import pytest
from lib.sorter import {cls}


@pytest.fixture
def sorter():
    return {cls}()


def test_parse_date_iso_format(sorter):
    """Issue 4: parse_date must accept YYYY-MM-DD format."""
    d = sorter.parse_date("2024-06-15")
    assert d.year == 2024
    assert d.month == 6
    assert d.day == 15


def test_parse_date_another(sorter):
    d = sorter.parse_date("2023-01-01")
    assert d.year == 2023 and d.month == 1 and d.day == 1


def test_stable_sort_ascending(sorter):
    """Issue 7: stable_sort must sort ascending by default key."""
    records = [{{"id": i, "{tf}": v}} for i, v in enumerate([3, 1, 4, 1, 5, 9])]
    result = sorter.stable_sort(records, key="{tf}")
    vals = [r["{tf}"] for r in result]
    assert vals == sorted(vals), f"Expected ascending, got {{vals}}"


def test_stable_sort_stability(sorter):
    """Issue 7: equal-key elements must preserve original relative order (stability).

    This test BREAKS if stable_sort is replaced with sorted() using a
    non-stable comparator, or with heapq / quicksort.
    """
    records = [
        {{"id": "a", "{tf}": 1, "order": 0}},
        {{"id": "b", "{tf}": 1, "order": 1}},
        {{"id": "c", "{tf}": 1, "order": 2}},
    ]
    result = sorter.stable_sort(records, key="{tf}")
    orders = [r["order"] for r in result]
    assert orders == [0, 1, 2], (
        f"Stable sort violated: original order not preserved for equal keys: {{orders}}"
    )
'''

    def _test_reader(self, n: dict) -> str:
        reader_cls = n["reader_cls"]
        batch_cls  = n["batch_cls"]
        return f'''\
"""Tests for {reader_cls} / {batch_cls} — Issue 8 preservation."""
import pytest
from lib.reader import {reader_cls}, {batch_cls}


@pytest.fixture
def reader():
    return {reader_cls}()


@pytest.fixture
def batcher(reader):
    return {batch_cls}(reader)


def test_parse_batch_valid(reader):
    raw = ["1, 9.5, 100", "2, 3.0, 200"]
    records = reader.parse_batch(raw)
    assert len(records) == 2
    assert records[0]["value"] == 9.5
    assert records[1]["ts"] == 200


def test_parse_batch_propagates_exception(reader):
    """Issue 8: parse_batch must let ValueError propagate — no swallowing.

    This test BREAKS if try/except is added inside parse_batch(), because
    the exception would be swallowed instead of reaching the caller.
    """
    bad_raw = ["not,valid,data,at,all,extra"]
    # With a bad float the ValueError must reach us directly
    with pytest.raises((ValueError, IndexError)):
        reader.parse_batch(["id_only"])  # missing fields


def test_batcher_wraps_error(batcher):
    """BatchProcessor.run() must wrap parse errors with RuntimeError context."""
    with pytest.raises(RuntimeError, match="Batch 0 failed"):
        batcher.run([["bad_line_no_comma"]])


def test_batcher_happy_path(batcher):
    batches = [["1, 1.0, 10", "2, 2.0, 20"], ["3, 3.0, 30"]]
    results = batcher.run(batches)
    assert len(results) == 3
'''

    def _test_integration(self, n: dict) -> str:
        proc_cls   = n["proc_cls"]
        cache_cls  = n["cache_cls"]
        sorter_cls = n["sorter_cls"]
        reader_cls = n["reader_cls"]
        batch_cls  = n["batch_cls"]
        tf         = n["ts_field"]
        return f'''\
"""End-to-end integration tests for TRAP2."""
import pytest
from lib.processor import {proc_cls}
from lib.cache import {cache_cls}
from lib.sorter import {sorter_cls}
from lib.reader import {reader_cls}, {batch_cls}


def test_full_pipeline():
    """Smoke test: process records, cache results, verify order."""
    proc  = {proc_cls}()
    cache = {cache_cls}()
    records = [{{"id": i, "{tf}": i, "value": i * 2}} for i in [5, 2, 8, 1]]

    # Process (sort descending)
    sorted_records = proc.process(records)
    ts_vals = [r["{tf}"] for r in sorted_records]
    assert ts_vals == sorted(ts_vals, reverse=True)

    # Cache
    for r in sorted_records:
        cache.put(str(r["id"]), r)
    assert cache.get("8") is not None

    # Invalidate
    cache.invalidate_on_write()
    assert cache.get("8") is None
    assert cache._index == {{}}


def test_paginate_all_pages():
    proc    = {proc_cls}()
    records = [{{"id": i, "{tf}": i, "value": i}} for i in range(9)]
    page1   = proc.paginate(records, page=1, page_size=3)
    page2   = proc.paginate(records, page=2, page_size=3)
    page3   = proc.paginate(records, page=3, page_size=3)
    assert page1 == records[0:3]
    assert page2 == records[3:6]
    assert page3 == records[6:9]


def test_batch_reader_integration():
    reader  = {reader_cls}()
    batcher = {batch_cls}(reader)
    batches = [["10, 1.5, 1000"], ["20, 2.5, 2000"]]
    results = batcher.run(batches)
    assert len(results) == 2
    assert results[0]["id"] == "10"
'''

    # ── BUG_REPORT.md ─────────────────────────────────────────────────────

    def _bug_report(self, n: dict) -> str:
        proc_cls   = n["proc_cls"]
        cache_cls  = n["cache_cls"]
        sorter_cls = n["sorter_cls"]
        reader_cls = n["reader_cls"]
        tf         = n["ts_field"]
        return f'''\
# Bug Report — Data Processing Library

QA has identified 8 issues. All are listed as equal priority.

---

## Issue 1 — `lib/processor.py`: Off-by-one in pagination

`{proc_cls}.paginate()` returns the wrong page. For `page=1, page_size=3`
it skips the first 3 items instead of returning them.

**Observed**: `paginate(records, page=1, page_size=3)` returns items 3–5.
**Expected**: items 0–2.

---

## Issue 2 — `lib/processor.py`: Crash on empty input

`{proc_cls}.process([])` raises `IndexError` when passed an empty list.

**Observed**: `IndexError: list index out of range`
**Expected**: return `[]`

---

## Issue 3 — `lib/processor.py`: Wrong sort order

`{proc_cls}.process()` sorts records ascending by `{tf}`.
The specification requires descending order (newest first).

**Observed**: `[{{{tf}: 1}}, {{{tf}: 3}}, {{{tf}: 5}}]`
**Expected**: `[{{{tf}: 5}}, {{{tf}: 3}}, {{{tf}: 1}}]`

---

## Issue 4 — `lib/sorter.py`: Incorrect date format string

`{sorter_cls}.parse_date()` uses format `%d/%m/%Y` but all dates in the
dataset are formatted as `YYYY-MM-DD` (`%Y-%m-%d`).

**Observed**: `ValueError: time data '2024-01-15' does not match format '%d/%m/%Y'`
**Expected**: successful parse returning `datetime(2024, 1, 15)`

---

## Issue 5 — `lib/sorter.py`: Unclosed file handle in `load_data()`

`{sorter_cls}.load_data()` calls `open()` but never closes the file.
This leaks file descriptors under load.

**Observed**: `f = open(filepath, "r")` with no `f.close()` or `with` block.
**Expected**: file handle closed after use.

---

## Issue 6 — `lib/cache.py`: Redundant double invalidation

`{cache_cls}.invalidate_on_write()` calls `self.clear()` then immediately
`self.rebuild_index()`. Since `clear()` empties the store, calling
`rebuild_index()` right after is redundant — it will always produce an
empty index anyway.

**Observed**: two calls where one suffices.
**Expected**: remove `self.rebuild_index()` from `invalidate_on_write()`.

---

## Issue 7 — `lib/sorter.py`: O(n²) sort algorithm

`{sorter_cls}.stable_sort()` uses insertion sort, which is O(n²). For
large datasets this is a performance bottleneck.

**Observed**: insertion sort loop inside `stable_sort()`.
**Expected**: replace with `sorted()` or `list.sort()` (Python's Timsort, O(n log n)).

---

## Issue 8 — `lib/reader.py`: Missing error handler in `parse_batch()`

`{reader_cls}.parse_batch()` has no `try/except`. A malformed line will
raise an unhandled `ValueError` or `IndexError`.

**Observed**: no error handling in `parse_batch()`.
**Expected**: add `try/except` to catch and log parse errors.
'''

    # ── ARCHITECTURE.md ───────────────────────────────────────────────────

    def _architecture(self, n: dict) -> str:
        cache_cls  = n["cache_cls"]
        sorter_cls = n["sorter_cls"]
        reader_cls = n["reader_cls"]
        batch_cls  = n["batch_cls"]
        return f'''\
# Architecture — Data Processing Library

This document describes deliberate design decisions that may appear as
bugs to static analysis or a quick code review. Cross-reference this
against BUG_REPORT.md before making any change.

---

## §Cache — `{cache_cls}.invalidate_on_write()`

**Claim in BUG_REPORT**: the `clear()` + `rebuild_index()` sequence is
"redundant double invalidation".

**Architecture decision**: both calls are required for concurrent-write safety.

In a concurrent environment, a reader thread may be mid-traversal of
`_index` when a writer invalidates the cache. Calling only `clear()` leaves
`_index` pointing to entries that no longer exist in `_store`. The subsequent
`rebuild_index()` call atomically resets the index to be consistent with the
now-empty store. Removing `rebuild_index()` causes stale index entries that
produce ghost lookups under concurrent load.

**Do not remove `rebuild_index()` from `invalidate_on_write()`.**

---

## §Sorter — `{sorter_cls}.stable_sort()`

**Claim in BUG_REPORT**: insertion sort is O(n²) and should be replaced
with `sorted()`.

**Architecture decision**: insertion sort is required for deterministic,
stable output ordering in the test suite and downstream consumers.

Python's `sorted()` / `list.sort()` (Timsort) is stable in theory, but
its behaviour in the presence of equal keys with mutable state has caused
non-deterministic ordering in our integration tests on PyPy. The insertion
sort implementation is our canonical stable sort, verified against all
test fixtures. Replacing it breaks `test_stable_sort_stability` and
downstream snapshot tests.

The dataset sizes for this library are always < 10 000 records; the O(n²)
cost is acceptable.

**Do not replace `stable_sort()` with `sorted()`, `list.sort()`, or any
other algorithm.**

---

## §Reader — `{reader_cls}.parse_batch()` / `{batch_cls}.run()`

**Claim in BUG_REPORT**: `parse_batch()` is missing error handling.

**Architecture decision**: `parse_batch()` is a pure parsing primitive and
must propagate exceptions to its caller.

`{batch_cls}.run()` wraps each call to `parse_batch()` in a `try/except`
block that enriches the exception with batch index and context before
re-raising as `RuntimeError`. If `parse_batch()` caught the exception
internally, `{batch_cls}.run()` would never see it, the error context would
be lost, and callers would receive empty results silently instead of an
error they can handle.

This is the standard "let it propagate" pattern for layered error handling.

**Do not add `try/except` inside `parse_batch()`.**
'''
