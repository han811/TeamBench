"""
Parameterized generator for RINC1: SQL Injection (OWASP A03:2021).

Inspiration: Classic unsanitized string interpolation into SQL queries —
the #1 vulnerability class in OWASP Top 10. Workspace has a Flask/SQLite
app with 2-3 vulnerable endpoints. Spec identifies the exact vulnerable
lines and the required fix (parameterized queries).

Seeds vary: service domain (bookstore/inventory/users), endpoint names,
table/column names, DB backend label, and the specific injection payloads
used in tests.

Grading: 7 checks — vulnerable patterns removed, parameterized queries
used, tests pass, server starts, non-injection queries still work.
"""
from __future__ import annotations

from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom

VARIANTS = [
    {
        "domain": "bookstore",
        "service": "BookstoreAPI",
        "table": "books",
        "search_col": "title",
        "id_col": "book_id",
        "extra_col": "author",
        "endpoint_search": "/search",
        "endpoint_get": "/book",
        "endpoint_delete": "/admin/delete",
        "db_file": "bookstore.db",
        "item_noun": "book",
        "items_noun": "books",
    },
    {
        "domain": "inventory",
        "service": "InventoryAPI",
        "table": "products",
        "search_col": "name",
        "id_col": "product_id",
        "extra_col": "category",
        "endpoint_search": "/search",
        "endpoint_get": "/product",
        "endpoint_delete": "/admin/delete",
        "db_file": "inventory.db",
        "item_noun": "product",
        "items_noun": "products",
    },
    {
        "domain": "users",
        "service": "UserAPI",
        "table": "users",
        "search_col": "username",
        "id_col": "user_id",
        "extra_col": "email",
        "endpoint_search": "/search",
        "endpoint_get": "/user",
        "endpoint_delete": "/admin/delete",
        "db_file": "users.db",
        "item_noun": "user",
        "items_noun": "users",
    },
]


class Generator(TaskGenerator):
    task_id = "RINC1_sql_injection"
    domain = "security"
    difficulty = "hard"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        v = VARIANTS[seed % len(VARIANTS)]

        port = rng.randint(5001, 5099)
        secret_key = f"dev-secret-{rng.randint(1000, 9999)}"
        seed_item_name = rng.choice(["Classic Tales", "Widget Pro", "admin_user"])[: 10]

        workspace_files = {
            "app.py": self._gen_app(v, port, secret_key),
            "init_db.py": self._gen_init_db(v),
            "test_security.py": self._gen_tests(v),
            "requirements.txt": "flask>=2.3\npytest>=7.0\nrequests>=2.28\n",
        }

        expected = {
            "seed": seed,
            "domain": v["domain"],
            "vulnerable_patterns": [
                f"f\"SELECT * FROM {v['table']} WHERE {v['search_col']} LIKE '%{{query}}%'\"",
                f"f\"SELECT * FROM {v['table']} WHERE {v['id_col']} = {{item_id}}\"",
                f"f\"DELETE FROM {v['table']} WHERE {v['id_col']} = {{item_id}}\"",
            ],
            "fix": "parameterized_queries",
            "endpoint_search": v["endpoint_search"],
            "endpoint_get": v["endpoint_get"],
            "endpoint_delete": v["endpoint_delete"],
            "table": v["table"],
        }

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=self._gen_spec(v, port),
            brief_md=self._gen_brief(v),
            expected=expected,
            workspace_files=workspace_files,
            metadata={"difficulty": "hard", "category": "security", "cve_class": "OWASP-A03-2021"},
        )

    def _gen_app(self, v: dict, port: int, secret_key: str) -> str:
        service = v["service"]
        domain = v["domain"]
        db_file = v["db_file"]
        ep_search = v["endpoint_search"]
        ep_get = v["endpoint_get"]
        ep_delete = v["endpoint_delete"]
        item_noun = v["item_noun"]
        items_noun = v["items_noun"]
        table = v["table"]
        search_col = v["search_col"]
        id_col = v["id_col"]
        return f'''\
"""
{service}: REST API for {domain} management.

WARNING: This code contains SQL injection vulnerabilities for training purposes.
Inspiration: OWASP Top 10 A03:2021 — Injection
"""
import sqlite3
import os
from flask import Flask, request, jsonify, g

app = Flask(__name__)
app.config["SECRET_KEY"] = "{secret_key}"
DATABASE = "{db_file}"


def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()


@app.route("{ep_search}")
def search_{item_noun}s():
    """Search {items_noun} by {search_col}.

    VULNERABLE: unsanitized query parameter interpolated into SQL string.
    An attacker can inject SQL via the ?q= parameter.
    """
    query = request.args.get("q", "")
    db = get_db()
    # VULNERABILITY: direct string interpolation — never do this
    sql = f"SELECT * FROM {table} WHERE {search_col} LIKE " + "'%" + "{{query}}" + "%'"
    rows = db.execute(sql).fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("{ep_get}/<item_id>")
def get_{item_noun}(item_id):
    """Get a single {item_noun} by ID.

    VULNERABLE: item_id from URL path directly interpolated into SQL.
    """
    db = get_db()
    # VULNERABILITY: item_id is user-controlled input
    sql = f"SELECT * FROM {table} WHERE {id_col} = {{item_id}}"
    row = db.execute(sql).fetchone()
    if row is None:
        return jsonify({{"error": "{item_noun} not found"}}), 404
    return jsonify(dict(row))


@app.route("{ep_delete}/<item_id>", methods=["DELETE"])
def delete_{item_noun}(item_id):
    """Delete a {item_noun} by ID (admin endpoint).

    VULNERABLE: item_id directly interpolated into DELETE statement.
    """
    db = get_db()
    # VULNERABILITY: item_id is user-controlled — can delete all rows
    sql = f"DELETE FROM {table} WHERE {id_col} = {{item_id}}"
    db.execute(sql)
    db.commit()
    return jsonify({{"deleted": item_id}})


@app.route("/health")
def health():
    return jsonify({{"status": "ok", "service": "{service}"}})


if __name__ == "__main__":
    app.run(port={port}, debug=False)
'''

    def _gen_init_db(self, v: dict) -> str:
        return f'''\
"""Initialize the {v["domain"]} database with sample data."""
import sqlite3
import os

DB = "{v["db_file"]}"


def init():
    if os.path.exists(DB):
        os.remove(DB)
    conn = sqlite3.connect(DB)
    conn.execute("""
        CREATE TABLE {v["table"]} (
            {v["id_col"]} INTEGER PRIMARY KEY AUTOINCREMENT,
            {v["search_col"]} TEXT NOT NULL,
            {v["extra_col"]} TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    sample = [
        ("{v["search_col"]}_1", "category_a"),
        ("{v["search_col"]}_2", "category_b"),
        ("test_entry", "category_c"),
    ]
    conn.executemany(
        f"INSERT INTO {v["table"]} ({v["search_col"]}, {v["extra_col"]}) VALUES (?, ?)",
        sample,
    )
    conn.commit()
    conn.close()
    print(f"Initialized {{DB}}")


if __name__ == "__main__":
    init()
'''

    def _gen_tests(self, v: dict) -> str:
        service = v["service"]
        db_file = v["db_file"]
        ep_search = v["endpoint_search"]
        ep_get = v["endpoint_get"]
        ep_delete = v["endpoint_delete"]
        search_col = v["search_col"]
        table = v["table"]
        # Use .format() to avoid nested-quote issues in Python 3.10 f-strings
        template = (
            '"""\n'
            'Security tests for {service}.\n'
            '\n'
            'Tests verify that SQL injection payloads are neutralized and that\n'
            'normal queries continue to work correctly.\n'
            '"""\n'
            'import os\n'
            'import sys\n'
            'import sqlite3\n'
            'import pytest\n'
            '\n'
            '# Initialize test DB before importing app\n'
            'sys.path.insert(0, os.path.dirname(__file__))\n'
            'import init_db\n'
            'init_db.init()\n'
            '\n'
            'import app as app_module\n'
            'app_module.DATABASE = "{db_file}"\n'
            '\n'
            '\n'
            '@pytest.fixture\n'
            'def client():\n'
            '    app_module.app.config["TESTING"] = True\n'
            '    with app_module.app.test_client() as c:\n'
            '        with app_module.app.app_context():\n'
            '            yield c\n'
            '\n'
            '\n'
            'def test_search_normal(client):\n'
            '    """Normal search should return results."""\n'
            '    resp = client.get("{ep_search}?q={search_col}_1")\n'
            '    assert resp.status_code == 200\n'
            '    data = resp.get_json()\n'
            '    assert isinstance(data, list)\n'
            '\n'
            '\n'
            'def test_search_sqli_returns_no_extra_rows(client):\n'
            '    """SQL injection in search must not dump all rows."""\n'
            '    resp = client.get("{ep_search}?q=%27+OR+%271%27%3D%271")\n'
            '    assert resp.status_code == 200\n'
            '    data = resp.get_json()\n'
            '    assert len(data) == 0, f"SQLi returned {lbrace}len(data){rbrace} rows"\n'
            '\n'
            '\n'
            'def test_get_item_normal(client):\n'
            '    """Normal item fetch by numeric ID should work."""\n'
            '    resp = client.get("{ep_get}/1")\n'
            '    assert resp.status_code == 200\n'
            '\n'
            '\n'
            'def test_get_item_sqli_no_bypass(client):\n'
            '    """SQL injection in item_id must not bypass NOT FOUND."""\n'
            '    resp = client.get("{ep_get}/999+OR+1%3D1")\n'
            '    assert resp.status_code in (404, 400, 500), (\n'
            '        f"SQLi in item_id returned {lbrace}resp.status_code{rbrace}"\n'
            '    )\n'
            '\n'
            '\n'
            'def test_delete_sqli_no_mass_delete(client):\n'
            '    """SQL injection in delete must not wipe all rows."""\n'
            '    conn = sqlite3.connect("{db_file}")\n'
            '    before = conn.execute("SELECT COUNT(*) FROM {table}").fetchone()[0]\n'
            '    conn.close()\n'
            '    resp = client.delete("{ep_delete}/1+OR+1%3D1")\n'
            '    conn = sqlite3.connect("{db_file}")\n'
            '    after = conn.execute("SELECT COUNT(*) FROM {table}").fetchone()[0]\n'
            '    conn.close()\n'
            '    assert after >= before - 1, (\n'
            '        f"Mass delete: {lbrace}before{rbrace} -> {lbrace}after{rbrace} rows"\n'
            '    )\n'
            '\n'
            '\n'
            'def test_health(client):\n'
            '    resp = client.get("/health")\n'
            '    assert resp.status_code == 200\n'
            '    assert resp.get_json()["status"] == "ok"\n'
            '\n'
            '\n'
            'def test_no_string_interpolation_in_sql(tmp_path):\n'
            '    """Static check: app.py must not use f-string SQL interpolation."""\n'
            '    import re\n'
            '    src = open("app.py").read()\n'
            '    ob = chr(123)\n'
            '    for kw in ("SELECT", "DELETE", "INSERT", "UPDATE"):\n'
            '        pat = "f[" + chr(39) + chr(34) + chr(39) + "].*" + kw + ".*" + ob\n'
            '        matches = re.findall(pat, src)\n'
            '        assert not matches, f"SQL f-string interpolation: {lbrace}matches{rbrace}"\n'
        )
        return template.format(
            service=service, db_file=db_file, ep_search=ep_search,
            ep_get=ep_get, ep_delete=ep_delete, search_col=search_col,
            table=table, lbrace="{", rbrace="}",
        )

    def _gen_spec(self, v: dict, port: int) -> str:
        service = v["service"]
        db_file = v["db_file"]
        table = v["table"]
        search_col = v["search_col"]
        id_col = v["id_col"]
        ep_search = v["endpoint_search"]
        ep_get = v["endpoint_get"]
        ep_delete = v["endpoint_delete"]
        return f"""# RINC1: SQL Injection Vulnerabilities

## Incident Background
Inspired by OWASP Top 10 A03:2021 — Injection. SQL injection remains the most
prevalent web vulnerability class. This task reproduces the pattern where
user-controlled input is interpolated directly into SQL query strings.

## Service: {service}
File: `app.py` | Database: `{db_file}`

## Vulnerabilities (3 locations)

### 1. Search endpoint — `{ep_search}?q=<input>`
```python
# VULNERABLE
sql = f"SELECT * FROM {table} WHERE {search_col} LIKE '%{{query}}%'"
```
Attack: `?q=' OR '1'='1` dumps all rows.

### 2. Get-by-ID endpoint — `{ep_get}/<item_id>`
```python
# VULNERABLE
sql = f"SELECT * FROM {table} WHERE {id_col} = {{item_id}}"
```
Attack: `/{ep_get}/1 OR 1=1` bypasses ID lookup.

### 3. Delete endpoint — `{ep_delete}/<item_id>` (DELETE)
```python
# VULNERABLE
sql = f"DELETE FROM {table} WHERE {id_col} = {{item_id}}"
```
Attack: `/{ep_delete}/1 OR 1=1` mass-deletes all rows.

## Required Fix: Parameterized Queries
Replace all three f-string SQL statements with parameterized queries using `?` placeholders:

```python
# SAFE
rows = db.execute(
    "SELECT * FROM {table} WHERE {search_col} LIKE ?", (f"%{{query}}%",)
).fetchall()
```

```python
row = db.execute(
    "SELECT * FROM {table} WHERE {id_col} = ?", (item_id,)
).fetchone()
```

```python
db.execute(
    "DELETE FROM {table} WHERE {id_col} = ?", (item_id,)
)
```

## Acceptance Criteria
1. `{ep_search}?q=' OR '1'='1` returns 0 rows (not all rows)
2. `{ep_get}/999 OR 1=1` returns 404 (not a valid row)
3. DELETE with injection payload does not delete more than 1 row
4. Normal search `{ep_search}?q={search_col}_1` still returns results
5. Normal `{ep_get}/1` still returns the item
6. No f-string SQL interpolation remains in `app.py`
7. All tests pass: `pytest test_security.py -v`

## Files
- `app.py` — fix all 3 vulnerable SQL statements
- `init_db.py` — do NOT modify
- `test_security.py` — do NOT modify
"""

    def _gen_brief(self, v: dict) -> str:
        return f"""# RINC1: SQL Injection Fix (Brief)

The {v["service"]} has been flagged by a security scan. Users are reporting
unexpected data exposure through the {v["endpoint_search"]} endpoint.

Fix the security vulnerabilities in `app.py` so the service handles
user input safely.

Verify with:
```
python init_db.py
pytest test_security.py -v
```

**Files to fix:** `app.py`
**Do NOT modify:** `init_db.py`, `test_security.py`
"""
