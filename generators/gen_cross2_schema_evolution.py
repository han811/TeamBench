"""
Parameterized generator for CROSS2: Schema Evolution.

Each seed produces a different domain (user management / product catalog /
order management) but the same structural challenge: Service B's ORM models
are stale after Service A ran a migration that renamed one column and added
three new columns. The Executor cannot fix this correctly without reading
Service A's migration and config — information the Planner must surface.
"""
from __future__ import annotations
import os
from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom


# ---------------------------------------------------------------------------
# Per-seed domain configuration
# ---------------------------------------------------------------------------
DOMAINS = [
    {
        # Seed 0 — User management
        "domain_label": "user management",
        "table": "users",
        "model_class": "User",
        "service_a_desc": "User authentication service",
        "service_b_desc": "User profile service",
        "app_a": "auth_service",
        "app_b": "profile_service",
        # Column rename: old -> new
        "old_col": "user_name",
        "new_col": "username",
        # Three new columns: (name, sql_type, sql_default, py_type_hint, py_default)
        "new_col_1": ("email_verified", "INTEGER", "0",       "int",  "0"),
        "new_col_2": ("last_login_at",  "TEXT",    "NULL",     "str",  "None"),
        "new_col_3": ("account_tier",   "TEXT",    "'free'",   "str",  "'free'"),
        # Config constants
        "config_const_name": "DEFAULT_TIER",
        "config_const_val": "free",
        "config_extra": [
            ("DEFAULT_EMAIL_VERIFIED", "False"),
            ("SESSION_TIMEOUT", "3600"),
            ("MAX_LOGIN_ATTEMPTS", "5"),
        ],
        # backfill column that gets the config default
        "tier_col_idx": 3,  # index in new_cols list (0-based)
    },
    {
        # Seed 1 — Product catalog
        "domain_label": "product catalog",
        "table": "products",
        "model_class": "Product",
        "service_a_desc": "Product inventory service",
        "service_b_desc": "Product listing service",
        "app_a": "inventory_service",
        "app_b": "listing_service",
        "old_col": "product_name",
        "new_col": "name",
        "new_col_1": ("is_published",  "INTEGER", "0",          "int", "0"),
        "new_col_2": ("published_at",  "TEXT",    "NULL",       "str", "None"),
        "new_col_3": ("pricing_tier",  "TEXT",    "'standard'", "str", "'standard'"),
        "config_const_name": "DEFAULT_PRICING_TIER",
        "config_const_val": "standard",
        "config_extra": [
            ("DEFAULT_PUBLISHED", "False"),
            ("CATALOG_VERSION", "2"),
            ("MAX_IMAGES_PER_PRODUCT", "10"),
        ],
        "tier_col_idx": 3,
    },
    {
        # Seed 2 — Order management
        "domain_label": "order management",
        "table": "orders",
        "model_class": "Order",
        "service_a_desc": "Order processing service",
        "service_b_desc": "Order fulfillment service",
        "app_a": "processing_service",
        "app_b": "fulfillment_service",
        "old_col": "order_ref",
        "new_col": "reference",
        "new_col_1": ("is_fulfilled",   "INTEGER", "0",        "int", "0"),
        "new_col_2": ("fulfilled_at",   "TEXT",    "NULL",     "str", "None"),
        "new_col_3": ("priority_level", "TEXT",    "'normal'", "str", "'normal'"),
        "config_const_name": "DEFAULT_PRIORITY",
        "config_const_val": "normal",
        "config_extra": [
            ("DEFAULT_FULFILLED", "False"),
            ("ORDER_EXPIRY_DAYS", "30"),
            ("MAX_ITEMS_PER_ORDER", "50"),
        ],
        "tier_col_idx": 3,
    },
]


class Generator(TaskGenerator):
    task_id = "CROSS2_schema_evolution"
    domain = "Data"
    difficulty = "hard"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        cfg = DOMAINS[seed % len(DOMAINS)]

        workspace_files = self._make_workspace(cfg)

        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", "CROSS2_schema_evolution"
        )
        with open(os.path.join(tasks_dir, "spec.md")) as f:
            spec_md = f.read()
        with open(os.path.join(tasks_dir, "brief.md")) as f:
            brief_md = f.read()

        nc1, nc2, nc3 = cfg["new_col_1"], cfg["new_col_2"], cfg["new_col_3"]

        return GeneratedTask(
            task_id="CROSS2_schema_evolution",
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "table": cfg["table"],
                "old_col": cfg["old_col"],
                "new_col": cfg["new_col"],
                "new_columns": [nc1[0], nc2[0], nc3[0]],
                "tier_default": cfg["config_const_val"],
                "seed": seed,
            },
            workspace_files=workspace_files,
            metadata={"difficulty": "hard", "category": "Data"},
        )

    # ------------------------------------------------------------------
    # Workspace construction
    # ------------------------------------------------------------------

    def _make_workspace(self, cfg: dict) -> dict[str, str]:
        files: dict[str, str] = {}
        t = cfg["table"]
        mc = cfg["model_class"]
        old = cfg["old_col"]
        new = cfg["new_col"]
        nc1, nc2, nc3 = cfg["new_col_1"], cfg["new_col_2"], cfg["new_col_3"]
        cname = cfg["config_const_name"]
        cval = cfg["config_const_val"]

        # ----------------------------------------------------------------
        # service_a — authoritative, correct service
        # ----------------------------------------------------------------
        files["service_a/__init__.py"] = ""

        files["service_a/config.py"] = self._make_config_a(cfg)

        files["service_a/models.py"] = self._make_models_a(cfg)

        files["service_a/app.py"] = f'''"""Service A — {cfg["service_a_desc"]}."""
import sqlite3
from service_a.models import {mc}
from shared.database import get_connection


def get_{t}():
    """Return all {t} from the database."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, {new}, email, {nc1[0]}, {nc2[0]}, {nc3[0]}, created_at FROM {t}"
    ).fetchall()
    conn.close()
    return [
        {mc}(
            id=row[0],
            {new}=row[1],
            email=row[2],
            {nc1[0]}=row[3],
            {nc2[0]}=row[4],
            {nc3[0]}=row[5],
            created_at=row[6],
        )
        for row in rows
    ]
'''

        files["service_a/migrations/__init__.py"] = ""

        files["service_a/migrations/001_initial.py"] = self._make_migration_001(cfg)

        files["service_a/migrations/002_add_columns.py"] = self._make_migration_002(cfg)

        # ----------------------------------------------------------------
        # service_b — stale service (needs fixing)
        # ----------------------------------------------------------------
        files["service_b/__init__.py"] = ""

        files["service_b/models.py"] = self._make_models_b_stale(cfg)

        files["service_b/queries.py"] = self._make_queries_b_stale(cfg)

        files["service_b/app.py"] = f'''"""Service B — {cfg["service_b_desc"]}."""
from shared.database import get_connection
from service_b.queries import get_{t[:-1] if t.endswith("s") else t}, get_all_{t}


def fetch_{t[:-1] if t.endswith("s") else t}(record_id: int):
    conn = get_connection()
    result = get_{t[:-1] if t.endswith("s") else t}(conn, record_id)
    conn.close()
    return result


def fetch_all_{t}():
    conn = get_connection()
    result = get_all_{t}(conn)
    conn.close()
    return result
'''

        # ----------------------------------------------------------------
        # shared — database helper + schema
        # ----------------------------------------------------------------
        files["shared/__init__.py"] = ""

        files["shared/database.py"] = self._make_shared_db(cfg)

        files["shared/schema.sql"] = self._make_schema_sql(cfg)

        # ----------------------------------------------------------------
        # scripts — backfill stub (needs implementation)
        # ----------------------------------------------------------------
        files["scripts/__init__.py"] = ""

        files["scripts/backfill.py"] = f'''"""Backfill script: populate new columns for existing {t}."""
# TODO: implement backfill
# Hint: import DEFAULT values from service_a.config
# Connect to the database via shared.database.get_connection()
# UPDATE {t} setting {nc1[0]}, {nc2[0]}, {nc3[0]} to their defaults
'''

        # ----------------------------------------------------------------
        # tests
        # ----------------------------------------------------------------
        files["tests/__init__.py"] = ""

        files["tests/test_cross_service.py"] = self._make_test_cross_service(cfg)

        files["tests/test_backfill.py"] = self._make_test_backfill(cfg)

        files["tests/test_migration.py"] = self._make_test_migration(cfg)

        return files

    # ------------------------------------------------------------------
    # File content helpers
    # ------------------------------------------------------------------

    def _make_config_a(self, cfg: dict) -> str:
        cname = cfg["config_const_name"]
        cval = cfg["config_const_val"]
        extras = "\n".join(f'{k} = {v}' for k, v in cfg["config_extra"])
        return f'''"""Configuration for Service A."""
{cname} = "{cval}"
{extras}
'''

    def _make_models_a(self, cfg: dict) -> str:
        t = cfg["table"]
        mc = cfg["model_class"]
        new = cfg["new_col"]
        nc1, nc2, nc3 = cfg["new_col_1"], cfg["new_col_2"], cfg["new_col_3"]
        cname = cfg["config_const_name"]
        return f'''"""Service A ORM models — updated to match current schema."""
from service_a.config import {cname}


class {mc}:
    """ORM model matching the current database schema."""

    def __init__(
        self,
        id: int,
        {new}: str,
        email: str = None,
        {nc1[0]}: {nc1[3]} = {nc1[4]},
        {nc2[0]}: {nc2[3]} = {nc2[4]},
        {nc3[0]}: {nc3[3]} = {nc3[4]},
        created_at: str = None,
    ):
        self.id = id
        self.{new} = {new}
        self.email = email
        self.{nc1[0]} = {nc1[0]}
        self.{nc2[0]} = {nc2[0]}
        self.{nc3[0]} = {nc3[0]}
        self.created_at = created_at

    @classmethod
    def from_row(cls, row):
        return cls(
            id=row[0],
            {new}=row[1],
            email=row[2],
            {nc1[0]}=row[3],
            {nc2[0]}=row[4],
            {nc3[0]}=row[5],
            created_at=row[6],
        )

    def __repr__(self):
        return f"{mc}(id={{self.id}}, {new}={{self.{new}!r}})"
'''

    def _make_models_b_stale(self, cfg: dict) -> str:
        t = cfg["table"]
        mc = cfg["model_class"]
        old = cfg["old_col"]
        nc1, nc2, nc3 = cfg["new_col_1"], cfg["new_col_2"], cfg["new_col_3"]
        return f'''"""Service B ORM models — NOTE: out of date with current schema."""


class {mc}:
    """ORM model for {t} records."""

    def __init__(self, id: int, {old}: str, email: str = None, created_at: str = None):
        self.id = id
        self.{old} = {old}
        self.email = email
        self.created_at = created_at
        # Missing: {nc1[0]}, {nc2[0]}, {nc3[0]}

    @classmethod
    def from_row(cls, row):
        return cls(row[0], row[1], row[2], row[3])

    def __repr__(self):
        return f"{mc}(id={{self.id}}, {old}={{self.{old}!r}})"
'''

    def _make_queries_b_stale(self, cfg: dict) -> str:
        t = cfg["table"]
        # singular form for get_<entity>
        singular = t[:-1] if t.endswith("s") else t
        mc = cfg["model_class"]
        return f'''"""Service B database queries."""
from service_b.models import {mc}


def get_{singular}(conn, record_id: int):
    """Fetch a single {singular} by ID."""
    row = conn.execute("SELECT * FROM {t} WHERE id = ?", (record_id,)).fetchone()
    if row is None:
        return None
    return {mc}.from_row(row)


def get_all_{t}(conn):
    """Fetch all {t}."""
    rows = conn.execute("SELECT * FROM {t}").fetchall()
    return [{mc}.from_row(row) for row in rows]
'''

    def _make_migration_001(self, cfg: dict) -> str:
        t = cfg["table"]
        old = cfg["old_col"]
        return f'''"""Migration 001: Create initial {t} table."""


def up(conn):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS {t} (
            id INTEGER PRIMARY KEY,
            {old} TEXT NOT NULL,
            email TEXT,
            created_at TEXT
        )
    """)
    conn.commit()


def down(conn):
    conn.execute("DROP TABLE IF EXISTS {t}")
    conn.commit()
'''

    def _make_migration_002(self, cfg: dict) -> str:
        t = cfg["table"]
        old = cfg["old_col"]
        new = cfg["new_col"]
        nc1, nc2, nc3 = cfg["new_col_1"], cfg["new_col_2"], cfg["new_col_3"]
        tier_default = f"'{cfg['config_const_val']}'"
        return f'''"""Migration 002: Add profile columns and rename {old}."""


def up(conn):
    cursor = conn.cursor()
    # SQLite does not support ALTER COLUMN RENAME directly.
    # Re-create the table with the updated schema.
    cursor.execute("""
        CREATE TABLE {t}_new (
            id INTEGER PRIMARY KEY,
            {new} TEXT NOT NULL,
            email TEXT,
            {nc1[0]} {nc1[1]} DEFAULT {nc1[2]},
            {nc2[0]} {nc2[1]} DEFAULT {nc2[2]},
            {nc3[0]} {nc3[1]} DEFAULT {tier_default},
            created_at TEXT
        )
    """)
    cursor.execute("""
        INSERT INTO {t}_new (id, {new}, email, created_at)
        SELECT id, {old}, email, created_at FROM {t}
    """)
    cursor.execute("DROP TABLE {t}")
    cursor.execute("ALTER TABLE {t}_new RENAME TO {t}")
    conn.commit()


def down(conn):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE {t}_old (
            id INTEGER PRIMARY KEY,
            {old} TEXT NOT NULL,
            email TEXT,
            created_at TEXT
        )
    """)
    cursor.execute("""
        INSERT INTO {t}_old (id, {old}, email, created_at)
        SELECT id, {new}, email, created_at FROM {t}
    """)
    cursor.execute("DROP TABLE {t}")
    cursor.execute("ALTER TABLE {t}_old RENAME TO {t}")
    conn.commit()
'''

    def _make_shared_db(self, cfg: dict) -> str:
        return '''"""Shared SQLite database connection helper."""
import os
import sqlite3

# Allow DB path override via environment variable (used in tests and backfill)
_DEFAULT_DB = "shared.db"


def get_db_path() -> str:
    return os.environ.get("DB_PATH", os.environ.get("DATABASE", _DEFAULT_DB))


def get_connection() -> sqlite3.Connection:
    """Return a sqlite3 connection to the shared database."""
    path = get_db_path()
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn
'''

    def _make_schema_sql(self, cfg: dict) -> str:
        t = cfg["table"]
        new = cfg["new_col"]
        nc1, nc2, nc3 = cfg["new_col_1"], cfg["new_col_2"], cfg["new_col_3"]
        tier_default = f"'{cfg['config_const_val']}'"
        return f'''-- Expected final schema (source of truth after migration 002)
-- Generated by CROSS2_schema_evolution

CREATE TABLE {t} (
    id INTEGER PRIMARY KEY,
    {new} TEXT NOT NULL,
    email TEXT,
    {nc1[0]} {nc1[1]} DEFAULT {nc1[2]},
    {nc2[0]} {nc2[1]} DEFAULT {nc2[2]},
    {nc3[0]} {nc3[1]} DEFAULT {tier_default},
    created_at TEXT
);
'''

    def _make_test_cross_service(self, cfg: dict) -> str:
        t = cfg["table"]
        mc = cfg["model_class"]
        old = cfg["old_col"]
        new = cfg["new_col"]
        nc1, nc2, nc3 = cfg["new_col_1"], cfg["new_col_2"], cfg["new_col_3"]
        singular = t[:-1] if t.endswith("s") else t
        return f'''"""Cross-service integration tests for CROSS2."""
import importlib.util
import os
import sqlite3
import tempfile
import pytest
import sys

# Ensure project root is on path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def _load_migration(rel_path):
    """Load a migration module by relative file path (avoids numeric-name import issue)."""
    abs_path = os.path.join(ROOT, rel_path)
    spec = importlib.util.spec_from_file_location("_migration", abs_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def db_path(tmp_path):
    """Create a temp DB, run both migrations, return path."""
    path = str(tmp_path / "test.db")
    os.environ["DB_PATH"] = path
    conn = sqlite3.connect(path)

    up1 = _load_migration("service_a/migrations/001_initial.py").up
    up2 = _load_migration("service_a/migrations/002_add_columns.py").up
    up1(conn)
    up2(conn)

    # Insert a test record
    conn.execute(
        "INSERT INTO {t} (id, {new}, email, created_at) VALUES (?, ?, ?, ?)",
        (1, "testuser", "test@example.com", "2024-01-01"),
    )
    conn.commit()
    conn.close()
    yield path
    os.environ.pop("DB_PATH", None)


def test_service_b_model_has_new_column(db_path):
    """Service B model must have the renamed column attribute."""
    from service_b.models import {mc}
    # {mc} must accept {new} kwarg (not {old})
    record = {mc}(id=1, {new}="alice", email="alice@example.com", created_at="2024-01-01")
    assert hasattr(record, "{new}"), "Model missing {new} attribute"
    assert not hasattr(record, "{old}"), "Model still has stale {old} attribute"


def test_service_b_model_has_new_fields(db_path):
    """Service B model must include all three new columns."""
    from service_b.models import {mc}
    record = {mc}(id=1, {new}="alice", email="alice@example.com", created_at="2024-01-01")
    assert hasattr(record, "{nc1[0]}"), "Model missing {nc1[0]}"
    assert hasattr(record, "{nc2[0]}"), "Model missing {nc2[0]}"
    assert hasattr(record, "{nc3[0]}"), "Model missing {nc3[0]}"


def test_service_b_queries_no_select_star(db_path):
    """Queries must use explicit column names, not SELECT *."""
    import service_b.queries as q
    import inspect
    src = inspect.getsource(q)
    assert "SELECT *" not in src, "service_b/queries.py still contains SELECT *"


def test_service_b_get_{singular}_returns_record(db_path):
    """get_{singular}() must return a {mc} with the correct column values."""
    import sqlite3 as _sq
    from service_b.queries import get_{singular}
    conn = _sq.connect(db_path)
    record = get_{singular}(conn, 1)
    conn.close()
    assert record is not None, "get_{singular}() returned None for existing record"
    assert hasattr(record, "{new}"), "Returned record missing {new}"
    assert getattr(record, "{new}") == "testuser"


def test_service_b_get_all_{t}(db_path):
    """get_all_{t}() must return a list of {mc} objects."""
    import sqlite3 as _sq
    from service_b.queries import get_all_{t}
    conn = _sq.connect(db_path)
    records = get_all_{t}(conn)
    conn.close()
    assert len(records) == 1
    assert hasattr(records[0], "{new}")
'''

    def _make_test_backfill(self, cfg: dict) -> str:
        t = cfg["table"]
        new = cfg["new_col"]
        nc1, nc2, nc3 = cfg["new_col_1"], cfg["new_col_2"], cfg["new_col_3"]
        cname = cfg["config_const_name"]
        cval = cfg["config_const_val"]
        return f'''"""Tests for the backfill script."""
import importlib.util
import os
import sqlite3
import subprocess
import sys
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def _load_migration(rel_path):
    abs_path = os.path.join(ROOT, rel_path)
    spec = importlib.util.spec_from_file_location("_migration", abs_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def pre_backfill_db(tmp_path):
    """Create DB after migration 002 with NULL values in new columns."""
    path = str(tmp_path / "backfill_test.db")
    os.environ["DB_PATH"] = path
    conn = sqlite3.connect(path)

    up1 = _load_migration("service_a/migrations/001_initial.py").up
    up2 = _load_migration("service_a/migrations/002_add_columns.py").up
    up1(conn)
    up2(conn)

    # Insert records with NULL new columns (simulating pre-backfill state)
    conn.execute(
        "INSERT INTO {t} (id, {new}, email, {nc1[0]}, {nc2[0]}, {nc3[0]}, created_at) "
        "VALUES (?, ?, ?, NULL, NULL, NULL, ?)",
        (1, "alice", "alice@example.com", "2024-01-01"),
    )
    conn.execute(
        "INSERT INTO {t} (id, {new}, email, {nc1[0]}, {nc2[0]}, {nc3[0]}, created_at) "
        "VALUES (?, ?, ?, NULL, NULL, NULL, ?)",
        (2, "bob", "bob@example.com", "2024-01-02"),
    )
    conn.commit()
    conn.close()
    yield path
    os.environ.pop("DB_PATH", None)


def test_backfill_runs_without_error(pre_backfill_db):
    """backfill.py must exit cleanly."""
    result = subprocess.run(
        [sys.executable, "scripts/backfill.py"],
        env={{**os.environ, "DB_PATH": pre_backfill_db}},
        capture_output=True, text=True
    )
    assert result.returncode == 0, (
        f"backfill.py failed with code {{result.returncode}}\\n"
        f"stdout: {{result.stdout}}\\nstderr: {{result.stderr}}"
    )


def test_backfill_sets_boolean_column(pre_backfill_db):
    """Backfill must explicitly set {nc1[0]} for all records (value 0 or False)."""
    # Verify the column is NULL before backfill (our fixture inserts NULL)
    conn = sqlite3.connect(pre_backfill_db)
    pre_rows = conn.execute("SELECT {nc1[0]} FROM {t}").fetchall()
    conn.close()
    assert all(r[0] is None for r in pre_rows), "Pre-condition: {nc1[0]} should be NULL before backfill"

    subprocess.run(
        [sys.executable, "scripts/backfill.py"],
        env={{**os.environ, "DB_PATH": pre_backfill_db}},
        capture_output=True
    )
    conn = sqlite3.connect(pre_backfill_db)
    rows = conn.execute("SELECT {nc1[0]} FROM {t}").fetchall()
    conn.close()
    for row in rows:
        assert row[0] in (0, False), f"Expected {nc1[0]}=0 after backfill, got {{row[0]}}"


def test_backfill_sets_tier_column_to_config_default(pre_backfill_db):
    """Backfill must set {nc3[0]} to the value of {cname} from service_a.config."""
    subprocess.run(
        [sys.executable, "scripts/backfill.py"],
        env={{**os.environ, "DB_PATH": pre_backfill_db}},
        capture_output=True
    )
    from service_a.config import {cname}
    conn = sqlite3.connect(pre_backfill_db)
    rows = conn.execute("SELECT {nc3[0]} FROM {t}").fetchall()
    conn.close()
    for row in rows:
        assert row[0] == {cname}, (
            f"Expected {nc3[0]}={{{cname}!r}}, got {{row[0]!r}}"
        )
'''

    def _make_test_migration(self, cfg: dict) -> str:
        t = cfg["table"]
        old = cfg["old_col"]
        new = cfg["new_col"]
        nc1, nc2, nc3 = cfg["new_col_1"], cfg["new_col_2"], cfg["new_col_3"]
        return f'''"""Tests for the migration scripts."""
import importlib.util
import os
import sqlite3
import sys
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def _load_migration(rel_path):
    abs_path = os.path.join(ROOT, rel_path)
    spec = importlib.util.spec_from_file_location("_migration", abs_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def conn(tmp_path):
    path = str(tmp_path / "migration_test.db")
    os.environ["DB_PATH"] = path
    c = sqlite3.connect(path)
    yield c
    c.close()
    os.environ.pop("DB_PATH", None)


def test_migration_001_creates_table(conn):
    up = _load_migration("service_a/migrations/001_initial.py").up
    up(conn)
    tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    assert "{t}" in tables


def test_migration_001_has_old_column(conn):
    up = _load_migration("service_a/migrations/001_initial.py").up
    up(conn)
    cols = [r[1] for r in conn.execute("PRAGMA table_info({t})")]
    assert "{old}" in cols, f"Migration 001 must create column {old}"


def test_migration_002_renames_column(conn):
    up1 = _load_migration("service_a/migrations/001_initial.py").up
    up2 = _load_migration("service_a/migrations/002_add_columns.py").up
    up1(conn)
    up2(conn)
    cols = [r[1] for r in conn.execute("PRAGMA table_info({t})")]
    assert "{new}" in cols, f"After migration 002, column {new} must exist"
    assert "{old}" not in cols, f"After migration 002, old column {old} must not exist"


def test_migration_002_adds_new_columns(conn):
    up1 = _load_migration("service_a/migrations/001_initial.py").up
    up2 = _load_migration("service_a/migrations/002_add_columns.py").up
    up1(conn)
    up2(conn)
    cols = [r[1] for r in conn.execute("PRAGMA table_info({t})")]
    assert "{nc1[0]}" in cols
    assert "{nc2[0]}" in cols
    assert "{nc3[0]}" in cols


def test_migration_002_preserves_data(conn):
    up1 = _load_migration("service_a/migrations/001_initial.py").up
    up2 = _load_migration("service_a/migrations/002_add_columns.py").up
    up1(conn)
    conn.execute("INSERT INTO {t} (id, {old}, email, created_at) VALUES (1, 'testval', 'x@y.com', '2024-01-01')")
    conn.commit()
    up2(conn)
    row = conn.execute("SELECT {new} FROM {t} WHERE id=1").fetchone()
    assert row is not None and row[0] == "testval", "Migration 002 must preserve existing row data"
'''
