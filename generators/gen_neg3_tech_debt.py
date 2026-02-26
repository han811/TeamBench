"""
Parameterized generator for NEG3: Tech Debt Prioritization.

Each seed produces:
  - Different application domain (inventory, billing, reporting, notification, auth)
  - Different set of 6 tech debt items drawn from a pool, each with seeded impact/effort scores
  - Different dependency constraint (one item blocks another)
  - Same challenge: pick the best 3 items to fix within a time budget, respecting dependencies

TNI Pattern C,A:
  - Spec has full prioritization matrix (impact x effort) and scoring rubric
  - Brief says "address tech debt" with no scoring details
  - Hidden constraint: one item depends on another (must fix dependency first)
  - Time budget: can only fix 3 of 6 items

Grading: correct items chosen, items fixed correctly, dependency order respected,
time budget not exceeded, highest-value items addressed first.
"""
from __future__ import annotations

import json

from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom

# ── Application domain profiles ───────────────────────────────────────────────

DOMAIN_CONFIGS = [
    {
        "domain": "inventory",
        "app_name": "InventoryService",
        "module_name": "inventory",
        "description": "warehouse inventory tracking service",
        "entity": "Product",
        "entity_plural": "products",
    },
    {
        "domain": "billing",
        "app_name": "BillingService",
        "module_name": "billing",
        "description": "customer billing and invoicing service",
        "entity": "Invoice",
        "entity_plural": "invoices",
    },
    {
        "domain": "reporting",
        "app_name": "ReportingService",
        "module_name": "reporting",
        "description": "business analytics and reporting service",
        "entity": "Report",
        "entity_plural": "reports",
    },
    {
        "domain": "notification",
        "app_name": "NotificationService",
        "module_name": "notification",
        "description": "user notification and alerting service",
        "entity": "Notification",
        "entity_plural": "notifications",
    },
    {
        "domain": "auth",
        "app_name": "AuthService",
        "module_name": "auth",
        "description": "user authentication and session management service",
        "entity": "User",
        "entity_plural": "users",
    },
]

# ── Tech debt item templates ───────────────────────────────────────────────────
# Each item has: id, category, title, description, impact (H/M/L), effort (H/M/L),
# fix_hours, and a template for the broken code pattern + fix.

TECH_DEBT_POOL = [
    {
        "id": "TD001",
        "category": "dead_code",
        "title": "Dead code: unused legacy processor",
        "description": "A legacy data processor function is never called but remains in the codebase, increasing cognitive load.",
        "impact": "low",
        "effort": "low",
        "fix_hours": 1,
        "fix_description": "Remove the unused `_legacy_process` function.",
        "grade_check": "no_legacy_process_function",
    },
    {
        "id": "TD002",
        "category": "missing_types",
        "title": "Missing type annotations on public API",
        "description": "Core public methods lack type annotations, making the API hard to use and error-prone.",
        "impact": "medium",
        "effort": "low",
        "fix_hours": 2,
        "fix_description": "Add type annotations to all public methods.",
        "grade_check": "type_annotations_present",
    },
    {
        "id": "TD003",
        "category": "duplicated_logic",
        "title": "Duplicated validation logic",
        "description": "Input validation is copy-pasted in three places instead of extracted to a shared function.",
        "impact": "high",
        "effort": "medium",
        "fix_hours": 3,
        "fix_description": "Extract duplicated validation into a single `_validate_input` helper.",
        "grade_check": "single_validate_function",
    },
    {
        "id": "TD004",
        "category": "hardcoded_values",
        "title": "Hardcoded configuration values",
        "description": "Timeout and retry limits are hardcoded as magic numbers scattered through the code.",
        "impact": "medium",
        "effort": "low",
        "fix_hours": 2,
        "fix_description": "Extract magic numbers into named constants at module top.",
        "grade_check": "named_constants_present",
    },
    {
        "id": "TD005",
        "category": "poor_error_handling",
        "title": "Bare except clauses swallow errors",
        "description": "Several bare `except:` clauses silently swallow exceptions, making debugging impossible.",
        "impact": "high",
        "effort": "medium",
        "fix_hours": 3,
        "fix_description": "Replace bare `except:` with specific exception types and re-raise or log properly.",
        "grade_check": "no_bare_except",
    },
    {
        "id": "TD006",
        "category": "missing_tests",
        "title": "Missing unit tests for core logic",
        "description": "The core processing function has zero test coverage, making refactoring risky.",
        "impact": "high",
        "effort": "high",
        "fix_hours": 6,
        "fix_description": "Add unit tests covering normal operation, edge cases, and error paths.",
        "grade_check": "tests_exist_and_pass",
    },
    {
        "id": "TD007",
        "category": "outdated_deps",
        "title": "Outdated dependency with known API deprecation",
        "description": "Uses a deprecated function from an internal utils library that will be removed next quarter.",
        "impact": "high",
        "effort": "low",
        "fix_hours": 2,
        "fix_description": "Replace `utils.old_format()` calls with the new `utils.format_data()` API.",
        "grade_check": "no_old_format_calls",
    },
    {
        "id": "TD008",
        "category": "missing_types",
        "title": "Missing return type on data transformer",
        "description": "The `transform` method returns different types in different code paths, confusing callers.",
        "impact": "medium",
        "effort": "low",
        "fix_hours": 1,
        "fix_description": "Normalise `transform` to always return the same type and add return annotation.",
        "grade_check": "transform_consistent_return",
    },
    {
        "id": "TD009",
        "category": "hardcoded_values",
        "title": "Hardcoded database connection string",
        "description": "Database connection string is hardcoded in source, making environment-specific config impossible.",
        "impact": "high",
        "effort": "low",
        "fix_hours": 2,
        "fix_description": "Read connection string from environment variable `DB_URL`.",
        "grade_check": "db_url_from_env",
    },
    {
        "id": "TD010",
        "category": "dead_code",
        "title": "Dead code: commented-out debug block",
        "description": "A large commented-out debug block (50+ lines) was never removed and confuses readers.",
        "impact": "low",
        "effort": "low",
        "fix_hours": 1,
        "fix_description": "Remove the commented-out debug block entirely.",
        "grade_check": "no_debug_comment_block",
    },
]

# ── Score matrix: impact x effort → value score (0-100) ──────────────────────
SCORE_MATRIX = {
    ("high",   "low"):    90,
    ("high",   "medium"): 60,
    ("high",   "high"):   30,
    ("medium", "low"):    70,
    ("medium", "medium"): 40,
    ("medium", "high"):   15,
    ("low",    "low"):    50,
    ("low",    "medium"): 20,
    ("low",    "high"):   5,
}

# ── Dependency pairs: (blocker_id, dependent_id) ──────────────────────────────
# blocker must be fixed before dependent. Only applicable if both are in the chosen 6.
DEPENDENCY_PAIRS = [
    ("TD009", "TD005"),  # fix DB URL before fixing error handling (DB calls would fail otherwise)
    ("TD004", "TD002"),  # fix constants before adding types (types reference constant names)
    ("TD007", "TD003"),  # fix deprecated API before deduplicating logic (dedup refactor uses new API)
    ("TD003", "TD006"),  # fix duplication before adding tests (tests target the extracted helper)
    ("TD004", "TD003"),  # fix constants before deduplicating (dedup uses named constants)
    ("TD007", "TD005"),  # fix deprecated API before error handling (error handling wraps API calls)
]

TIME_BUDGET_HOURS = 6  # can fix at most 3 of 6 items given realistic hours


def _pick_items(rng: SeededRandom, n_total: int = 6) -> list[dict]:
    """Pick n_total unique items from the pool, seeded-randomly."""
    indices = rng.sample(list(range(len(TECH_DEBT_POOL))), n_total)
    return [dict(TECH_DEBT_POOL[i]) for i in indices]


def _find_dependency(items: list[dict]) -> tuple[str, str] | None:
    """
    Find the first applicable dependency pair given the chosen items.
    Returns (blocker_id, dependent_id) or None.
    """
    ids = {item["id"] for item in items}
    for blocker, dependent in DEPENDENCY_PAIRS:
        if blocker in ids and dependent in ids:
            return (blocker, dependent)
    return None


def _compute_value(item: dict) -> int:
    return SCORE_MATRIX[(item["impact"], item["effort"])]


def _optimal_selection(items: list[dict], dependency: tuple[str, str] | None,
                        budget_hours: int, n_pick: int = 3) -> list[str]:
    """
    Greedy selection of the highest-value items within budget, respecting dependency.
    Returns list of IDs in fix order.
    """
    # Sort by value descending
    ranked = sorted(items, key=lambda x: _compute_value(x), reverse=True)

    selected_ids: list[str] = []
    total_hours = 0

    for item in ranked:
        if len(selected_ids) >= n_pick:
            break
        if total_hours + item["fix_hours"] > budget_hours:
            continue
        selected_ids.append(item["id"])
        total_hours += item["fix_hours"]

    # Enforce dependency ordering in selected set
    if dependency:
        blocker, dependent = dependency
        if blocker in selected_ids and dependent in selected_ids:
            bi = selected_ids.index(blocker)
            di = selected_ids.index(dependent)
            if bi > di:
                # Swap to put blocker first
                selected_ids[bi], selected_ids[di] = selected_ids[di], selected_ids[bi]
        elif dependent in selected_ids and blocker not in selected_ids:
            # If dependent is selected but blocker is not, include blocker instead of lowest-value item
            # Only do this if blocker fits in budget
            blocker_item = next((i for i in items if i["id"] == blocker), None)
            if blocker_item:
                new_hours = sum(i["fix_hours"] for i in items if i["id"] in selected_ids) \
                            - next(i["fix_hours"] for i in items if i["id"] == selected_ids[-1]) \
                            + blocker_item["fix_hours"]
                if new_hours <= budget_hours:
                    selected_ids[-1] = blocker["id"] if isinstance(blocker, dict) else blocker
                    selected_ids.insert(selected_ids.index(dependent), blocker if isinstance(blocker, str) else blocker["id"])
                    selected_ids = list(dict.fromkeys(selected_ids))[:n_pick]

    return selected_ids


class Generator(TaskGenerator):
    task_id = "NEG3_tech_debt"
    domain = "software"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        domain_cfg = DOMAIN_CONFIGS[seed % len(DOMAIN_CONFIGS)]

        # Pick 6 items from pool
        items = _pick_items(rng, n_total=6)

        # Find applicable dependency
        dependency = _find_dependency(items)

        # Compute values for all items
        for item in items:
            item["value_score"] = _compute_value(item)

        # Compute optimal selection
        optimal_ids = _optimal_selection(items, dependency, TIME_BUDGET_HOURS, n_pick=3)
        optimal_hours = sum(i["fix_hours"] for i in items if i["id"] in optimal_ids)

        expected = {
            "domain": domain_cfg["domain"],
            "seed": seed,
            "items_presented": [i["id"] for i in items],
            "optimal_selection": optimal_ids,
            "optimal_hours": optimal_hours,
            "time_budget_hours": TIME_BUDGET_HOURS,
            "dependency": list(dependency) if dependency else None,
            "item_scores": {i["id"]: i["value_score"] for i in items},
            "checks": {
                "items_chosen_count": 3,
                "budget_not_exceeded": True,
                "dependency_order_respected": True,
                "highest_value_items_selected": True,
                "items_actually_fixed": True,
            },
        }

        workspace_files = self._build_workspace(domain_cfg, items, dependency, rng, seed)
        spec_md = self._generate_spec(domain_cfg, items, dependency)
        brief_md = self._generate_brief(domain_cfg)

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected=expected,
            workspace_files=workspace_files,
        )

    # ------------------------------------------------------------------
    # Workspace builder
    # ------------------------------------------------------------------
    def _build_workspace(self, domain_cfg: dict, items: list[dict],
                         dependency: tuple[str, str] | None,
                         rng: SeededRandom, seed: int) -> dict[str, str]:
        files: dict[str, str] = {}
        mod = domain_cfg["module_name"]
        app = domain_cfg["app_name"]
        entity = domain_cfg["entity"]
        entity_pl = domain_cfg["entity_plural"]

        item_ids = {i["id"] for i in items}

        # Determine which patterns to embed based on selected items
        has_dead_code = any(i["category"] == "dead_code" and i["id"] in item_ids for i in items)
        has_types = any(i["category"] == "missing_types" and i["id"] in item_ids for i in items)
        has_dup = "TD003" in item_ids
        has_constants = "TD004" in item_ids
        has_bare_except = "TD005" in item_ids
        has_tests = "TD006" in item_ids
        has_old_api = "TD007" in item_ids
        has_transform = "TD008" in item_ids
        has_db_url = "TD009" in item_ids
        has_debug_comment = "TD010" in item_ids

        # ── utils.py (internal dep) ───────────────────────────────────────────
        files["utils.py"] = f'''"""Internal utilities — {domain_cfg["description"]}."""


def old_format(data: dict) -> str:
    """Deprecated: use format_data() instead. Will be removed Q3."""
    import json
    return json.dumps(data, sort_keys=True)


def format_data(data: dict, *, indent: int = 2) -> str:
    """Format data for output. Preferred API."""
    import json
    return json.dumps(data, indent=indent, sort_keys=True)


def parse_id(raw: str) -> int:
    """Parse a string ID to integer."""
    return int(raw.strip())
'''

        # ── service.py — the main file with all the tech debt ─────────────────
        dead_legacy = ""
        if has_dead_code and any(i["id"] == "TD001" for i in items):
            dead_legacy = '''

def _legacy_process(data: dict) -> dict:
    """Legacy processor — no longer used since v1.2."""
    # This function is never called anywhere in the codebase.
    result = {}
    for k, v in data.items():
        result[k] = str(v).upper()
    # Old transformation pipeline
    if "id" in result:
        result["legacy_id"] = result.pop("id")
    return result
'''

        debug_block = ""
        if has_debug_comment:
            debug_block = '''        # ---- DEBUG BLOCK (do not commit) ----
        # import pdb; pdb.set_trace()
        # print("DEBUG: entering process")
        # print(f"DEBUG: data={data}")
        # print(f"DEBUG: type={type(data)}")
        # for k, v in data.items():
        #     print(f"DEBUG:   {k!r} -> {v!r}")
        # print("DEBUG: validation start")
        # is_ok = True
        # for field in required_fields:
        #     if field not in data:
        #         is_ok = False
        #         print(f"DEBUG: missing field {field!r}")
        # print(f"DEBUG: validation ok={is_ok}")
        # print("DEBUG: processing start")
        # result = self._run(data)
        # print(f"DEBUG: result={result}")
        # print("DEBUG: done")
        # ---- END DEBUG BLOCK ----
'''

        # Magic numbers or named constants
        if has_constants:
            constants_block = '''# TODO: extract these magic numbers to named constants
'''
            timeout_val = "30"
            retry_val = "3"
            max_size_val = "1000"
        else:
            constants_block = """TIMEOUT_SECONDS = 30
MAX_RETRIES = 3
MAX_BATCH_SIZE = 1000
"""
            timeout_val = "TIMEOUT_SECONDS"
            retry_val = "MAX_RETRIES"
            max_size_val = "MAX_BATCH_SIZE"

        # DB URL
        if has_db_url:
            db_conn = f'DB_URL = "postgresql://admin:secret@localhost:5432/{mod}_db"'
        else:
            db_conn = 'DB_URL = os.environ.get("DB_URL", "postgresql://localhost:5432/app_db")'

        # Old API calls
        if has_old_api:
            format_call = "utils.old_format(record)"
            format_import = "import utils"
        else:
            format_call = "utils.format_data(record)"
            format_import = "import utils"

        # Type annotations
        if has_types:
            # no type annotations on public methods
            process_sig = "def process(self, data):"
            fetch_sig = "def fetch(self, entity_id):"
            delete_sig = "def delete(self, entity_id):"
        else:
            process_sig = f"def process(self, data: dict) -> dict:"
            fetch_sig = f"def fetch(self, entity_id: int) -> dict | None:"
            delete_sig = f"def delete(self, entity_id: int) -> bool:"

        # Transform inconsistency
        if has_transform:
            transform_body = f'''    def transform(self, record):
        """Transform a {entity} record for output."""
        if not record:
            return None  # BUG: sometimes returns None, sometimes dict
        if record.get("active"):
            return {{{{"id": record["id"], "name": record.get("name", "")}}}}
        return record  # BUG: returns full dict in this branch
'''
        else:
            transform_body = f'''    def transform(self, record: dict | None) -> dict:
        """Transform a {entity} record for output."""
        if not record:
            return {{}}
        return {{{{"id": record["id"], "name": record.get("name", "")}}}}
'''

        # Bare except or specific exceptions
        if has_bare_except:
            fetch_body = f'''    {fetch_sig}
        """Fetch a single {entity} by ID."""
        try:
            record = self._db.get({mod}_id=entity_id)
            return self.transform(record)
        except:  # noqa: E722  BUG: bare except swallows all errors
            return None

    {delete_sig}
        """Delete a {entity} by ID."""
        try:
            self._db.delete(entity_id)
            return True
        except:  # noqa: E722  BUG: bare except swallows all errors
            return False
'''
        else:
            fetch_body = f'''    {fetch_sig}
        """Fetch a single {entity} by ID."""
        try:
            record = self._db.get({mod}_id=entity_id)
            return self.transform(record)
        except KeyError:
            return None
        except Exception as exc:
            raise RuntimeError(f"DB fetch failed: {{exc}}") from exc

    {delete_sig}
        """Delete a {entity} by ID."""
        try:
            self._db.delete(entity_id)
            return True
        except KeyError:
            return False
        except Exception as exc:
            raise RuntimeError(f"DB delete failed: {{exc}}") from exc
'''

        # Duplicated validation
        if has_dup:
            validation_inline = f'''        # Validate: duplicated inline (also in fetch and delete)
        if not isinstance(data, dict):
            raise ValueError("data must be a dict")
        if "id" not in data:
            raise ValueError("id is required")
        if not isinstance(data.get("id"), int):
            raise ValueError("id must be an integer")
'''
            fetch_validation = f'''        # Validate: duplicated inline (copy-paste from process)
        if not isinstance(entity_id, (int, str)):
            raise ValueError("entity_id must be int or str")
        if entity_id is None:
            raise ValueError("id is required")
'''
        else:
            validation_inline = "        self._validate_input(data)\n"
            fetch_validation = "        self._validate_input(entity_id)\n"

        service_py = f'''"""
{app}: {domain_cfg["description"]}.

Technical debt items present in this file:
{chr(10).join(f"  - [{i['id']}] {i['title']}" for i in items)}
"""
from __future__ import annotations

import os
{format_import}

{constants_block}
{db_conn}


class _FakeDB:
    """Stub DB for demonstration."""

    def __init__(self):
        self._store: dict[int, dict] = {{}}

    def get(self, **kwargs) -> dict | None:
        key = next(iter(kwargs.values()))
        return self._store.get(int(key))

    def save(self, record: dict) -> dict:
        self._store[record["id"]] = record
        return record

    def delete(self, entity_id: int) -> None:
        self._store.pop(int(entity_id), None)

    def list_all(self) -> list[dict]:
        return list(self._store.values())


class {app}:
    """{entity} management service."""

    def __init__(self):
        self._db = _FakeDB()

    {process_sig}
        """Process and store a {entity} record.

        Timeout: {timeout_val}s, max retries: {retry_val}.
        """
{debug_block}{validation_inline}
        if len(data) > {max_size_val}:
            raise ValueError("Batch too large")

        record = dict(data)
        formatted = {format_call}
        record["_formatted"] = formatted

        attempt = 0
        while attempt < {retry_val}:
            try:
                return self._db.save(record)
            except Exception as exc:
                attempt += 1
                if attempt >= {retry_val}:
                    raise RuntimeError(f"Save failed after {{{retry_val}}} retries") from exc

        return record

    def list_all(self) -> list[dict]:
        """Return all {entity_pl}."""
        return self._db.list_all()

{transform_body}
{fetch_body}
'''
        # Append module-level dead code after the class (outside f-string to avoid {{ }} escaping)
        service_py += dead_legacy
        # Remove extra blank lines
        import re
        service_py = re.sub(r'\n{4,}', '\n\n\n', service_py)

        files["service.py"] = service_py

        # ── validate_input helper (only if dup is fixed) — not present in buggy version
        # (it's absent; agents must create it)

        # ── tests/test_service.py ─────────────────────────────────────────────
        if has_tests:
            # Minimal stub — agents must fill this in
            files["tests/__init__.py"] = ""
            files["tests/test_service.py"] = f'''"""Unit tests for {app}.

TODO: This test file is a stub. Add tests for:
  - Normal {entity.lower()} processing
  - Edge cases (empty dict, missing id, oversized batch)
  - Error paths (DB failures)
"""
import pytest
# from service import {app}


def test_placeholder():
    """Placeholder — replace with real tests."""
    assert True
'''
        else:
            files["tests/__init__.py"] = ""
            files["tests/test_service.py"] = f'''"""Unit tests for {app}."""
import pytest
from service import {app}


def test_process_valid():
    svc = {app}()
    result = svc.process({{"id": 1, "name": "test"}})
    assert result["id"] == 1


def test_process_missing_id():
    svc = {app}()
    with pytest.raises((ValueError, KeyError)):
        svc.process({{"name": "no_id"}})


def test_list_all_empty():
    svc = {app}()
    assert svc.list_all() == []


def test_delete():
    svc = {app}()
    svc.process({{"id": 42, "name": "to_delete"}})
    result = svc.delete(42)
    assert result is True
'''

        # ── tech_debt.json — machine-readable registry for grader ─────────────
        item_records = []
        for item in items:
            rec = {
                "id": item["id"],
                "category": item["category"],
                "title": item["title"],
                "impact": item["impact"],
                "effort": item["effort"],
                "fix_hours": item["fix_hours"],
                "value_score": item["value_score"],
            }
            item_records.append(rec)

        dep_record = None
        if dependency:
            dep_record = {"blocker": dependency[0], "dependent": dependency[1]}

        files["tech_debt.json"] = json.dumps({
            "items": item_records,
            "time_budget_hours": TIME_BUDGET_HOURS,
            "max_items_to_fix": 3,
            "dependency": dep_record,
        }, indent=2) + "\n"

        # ── prioritize.py — output file agents must produce ───────────────────
        files["prioritize.py"] = f'''"""
Tech debt prioritization script.

Edit `plan` below to declare which items you will fix and in what order.
Then run: python prioritize.py

The script validates your plan against the time budget and dependency rules.
"""
import json

# ── Your plan ─────────────────────────────────────────────────────────────────
# List the IDs of the tech debt items you will fix, in the order you will fix them.
# You may fix at most 3 items within the {TIME_BUDGET_HOURS}-hour time budget.
PLAN: list[str] = [
    # e.g. "TD001", "TD002", "TD003"
]

# ── Validation ────────────────────────────────────────────────────────────────

def validate_plan(plan: list[str], registry_path: str = "tech_debt.json") -> dict:
    with open(registry_path) as f:
        registry = json.load(f)

    items_by_id = {{item["id"]: item for item in registry["items"]}}
    budget = registry["time_budget_hours"]
    max_items = registry["max_items_to_fix"]
    dependency = registry.get("dependency")

    issues = []

    # Check: all IDs are valid
    for tid in plan:
        if tid not in items_by_id:
            issues.append(f"Unknown item ID: {{tid}}")

    # Check: at most max_items
    if len(plan) > max_items:
        issues.append(f"Plan selects {{len(plan)}} items but max is {{max_items}}")

    # Check: time budget
    total_hours = sum(items_by_id[tid]["fix_hours"] for tid in plan if tid in items_by_id)
    if total_hours > budget:
        issues.append(f"Plan requires {{total_hours}}h but budget is {{budget}}h")

    # Check: dependency order
    if dependency:
        blocker = dependency["blocker"]
        dependent = dependency["dependent"]
        if blocker in plan and dependent in plan:
            if plan.index(blocker) > plan.index(dependent):
                issues.append(
                    f"Dependency violation: {{blocker}} must come before {{dependent}}"
                )
        elif dependent in plan and blocker not in plan:
            issues.append(
                f"Dependency violation: {{dependent}} requires {{blocker}} to be fixed first"
            )

    # Compute value
    total_value = sum(items_by_id[tid]["value_score"] for tid in plan if tid in items_by_id)

    return {{
        "plan": plan,
        "total_hours": total_hours,
        "total_value": total_value,
        "budget_hours": budget,
        "dependency": dependency,
        "issues": issues,
        "valid": len(issues) == 0,
    }}


def main():
    import sys
    result = validate_plan(PLAN)

    print("=== TECH DEBT PRIORITIZATION PLAN ===")
    print(f"Items selected: {{len(result['plan'])}} / 3 max")
    print(f"Total hours:    {{result['total_hours']}} / {{result['budget_hours']}} budget")
    print(f"Total value:    {{result['total_value']}} points")
    print()

    if result["dependency"]:
        dep = result["dependency"]
        print(f"Dependency constraint: {{dep['blocker']}} must precede {{dep['dependent']}}")
    print()

    if result["issues"]:
        print("VALIDATION ISSUES:")
        for issue in result["issues"]:
            print(f"  - {{issue}}")
        print()
        print("PLAN INVALID")
        sys.exit(1)
    else:
        print("PLAN VALID")
        sys.exit(0)


if __name__ == "__main__":
    main()
'''

        return files

    # ------------------------------------------------------------------
    # Spec / brief generators
    # ------------------------------------------------------------------
    def _generate_spec(self, domain_cfg: dict, items: list[dict],
                       dependency: tuple[str, str] | None) -> str:
        app = domain_cfg["app_name"]
        desc = domain_cfg["description"]

        # Impact x effort matrix display
        matrix_rows = []
        for impact in ["high", "medium", "low"]:
            row = f"| {impact.capitalize():6} |"
            for effort in ["low", "medium", "high"]:
                row += f" {SCORE_MATRIX[(impact, effort)]:>6} |"
            matrix_rows.append(row)
        matrix_str = "\n".join(matrix_rows)

        # Item table
        item_rows = []
        for item in items:
            value = item["value_score"]
            dep_note = ""
            if dependency:
                if item["id"] == dependency[0]:
                    dep_note = f" *(blocks {dependency[1]})*"
                elif item["id"] == dependency[1]:
                    dep_note = f" *(requires {dependency[0]})*"
            item_rows.append(
                f"| {item['id']} | {item['title'][:42]}{dep_note} | "
                f"{item['impact'].capitalize():6} | {item['effort'].capitalize():6} | "
                f"{item['fix_hours']}h | {value:>5} |"
            )
        items_table = "\n".join(item_rows)

        dep_section = ""
        if dependency:
            blocker = next(i for i in items if i["id"] == dependency[0])
            dependent = next(i for i in items if i["id"] == dependency[1])
            dep_section = f"""
## Dependency Constraint

**{dependency[0]} must be completed before {dependency[1]}.**

- {dependency[0]}: {blocker['title']}
- {dependency[1]}: {dependent['title']}

If you select {dependency[1]}, you must also select {dependency[0]} and schedule it first.
Selecting {dependency[1]} without {dependency[0]} will fail the dependency check.
"""

        return f"""# NEG3: Tech Debt Prioritization

## System Under Review
**Service**: {app} — {desc}

The codebase has accumulated 6 tech debt items. You must prioritize and fix exactly 3 of them
within the available time budget.

## Time Budget
**Hard limit: {TIME_BUDGET_HOURS} hours total.** Selecting items whose combined `fix_hours`
exceeds {TIME_BUDGET_HOURS} hours will fail the budget check.

## Scoring Matrix

Use this matrix to score each item. Address **highest-value items first** (highest impact,
lowest effort = highest value score).

| Impact \\ Effort | Low  | Medium | High |
|-----------------|------|--------|------|
{matrix_str}

## Tech Debt Backlog

The following items have been identified. Review them carefully — their value scores determine
the optimal selection.

| ID    | Title | Impact | Effort | Hours | Score |
|-------|-------|--------|--------|-------|-------|
{items_table}
{dep_section}
## Prioritization Rubric

1. **Score each item** using the Impact × Effort matrix above.
2. **Select the 3 highest-scoring items** that fit within the {TIME_BUDGET_HOURS}-hour budget.
3. **Respect the dependency constraint** — if you select a dependent item, you must also
   select and schedule its blocker first.
4. **Fix the selected items** in `service.py` (and `tests/test_service.py` if applicable).
5. **Declare your plan** in `prioritize.py` by setting the `PLAN` list, then run
   `python prioritize.py` to validate.

## Deliverables

1. **`prioritize.py`** — `PLAN` list populated with exactly 3 item IDs in fix order.
   Running `python prioritize.py` must exit 0.
2. **`service.py`** — Selected tech debt items actually fixed (not just declared).
3. **`tests/test_service.py`** — If TD006 is in your plan, the stub must be replaced with
   real tests that pass under `pytest`.

## Grading Checks (10+)

| Check | Description |
|-------|-------------|
| `plan_valid_json` | `prioritize.py` runs without error and exits 0 |
| `exactly_3_items` | Plan selects exactly 3 items |
| `budget_not_exceeded` | Total fix_hours <= {TIME_BUDGET_HOURS} |
| `dependency_order` | Blocker precedes dependent (if both selected) |
| `dependent_without_blocker` | Dependent not selected without blocker |
| `highest_value_items` | All 3 selected items are in the top-4 by score |
| `no_bare_except` | No bare `except:` in service.py (if TD005 fixed) |
| `named_constants` | Magic numbers extracted to constants (if TD004 fixed) |
| `no_old_format` | No `old_format()` calls (if TD007 fixed) |
| `type_annotations` | Public methods have type annotations (if TD002 fixed) |
| `no_legacy_function` | `_legacy_process` removed (if TD001 fixed) |
| `no_debug_block` | Debug comment block removed (if TD010 fixed) |
| `tests_pass` | `pytest` exits 0 (if TD006 fixed) |

## Common Traps

- **Fixing the cheapest items** (low hours) without considering value leads to low total score.
- **Ignoring the dependency**: selecting the dependent without the blocker fails the check.
- **Declaring but not fixing**: the `PLAN` list is checked against actual code changes.
- **Exceeding budget**: 4+ items or items whose hours sum > {TIME_BUDGET_HOURS} fails immediately.
"""

    def _generate_brief(self, domain_cfg: dict) -> str:
        app = domain_cfg["app_name"]
        desc = domain_cfg["description"]
        return f"""# NEG3: Tech Debt Prioritization (Brief)

The {app} ({desc}) has accumulated technical debt. Address the most important items.

There are 6 identified tech debt items. Review `tech_debt.json` for the full list.
You can only fix 3 items within the available time budget.

Declare your plan in `prioritize.py` (set the `PLAN` list), then fix the selected items
in `service.py` (and `tests/test_service.py` if needed).

Validate with: `python prioritize.py`
Test with: `pytest tests/`
"""
