"""
Security tests for InventoryAPI.

Tests verify that SQL injection payloads are neutralized and that
normal queries continue to work correctly.
"""
import os
import sys
import sqlite3
import pytest

# Initialize test DB before importing app
sys.path.insert(0, os.path.dirname(__file__))
import init_db
init_db.init()

import app as app_module
app_module.DATABASE = "inventory.db"


@pytest.fixture
def client():
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as c:
        with app_module.app.app_context():
            yield c


def test_search_normal(client):
    """Normal search should return results."""
    resp = client.get("/search?q=name_1")
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)


def test_search_sqli_returns_no_extra_rows(client):
    """SQL injection in search must not dump all rows."""
    resp = client.get("/search?q=%27+OR+%271%27%3D%271")
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) == 0, f"SQLi returned {len(data)} rows"


def test_get_item_normal(client):
    """Normal item fetch by numeric ID should work."""
    resp = client.get("/product/1")
    assert resp.status_code == 200


def test_get_item_sqli_no_bypass(client):
    """SQL injection in item_id must not bypass NOT FOUND."""
    resp = client.get("/product/999+OR+1%3D1")
    assert resp.status_code in (404, 400, 500), (
        f"SQLi in item_id returned {resp.status_code}"
    )


def test_delete_sqli_no_mass_delete(client):
    """SQL injection in delete must not wipe all rows."""
    conn = sqlite3.connect("inventory.db")
    before = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    conn.close()
    resp = client.delete("/admin/delete/1+OR+1%3D1")
    conn = sqlite3.connect("inventory.db")
    after = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    conn.close()
    assert after >= before - 1, (
        f"Mass delete: {before} -> {after} rows"
    )


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"


def test_no_string_interpolation_in_sql(tmp_path):
    """Static check: app.py must not use f-string SQL interpolation."""
    import re
    src = open("app.py").read()
    ob = chr(123)
    for kw in ("SELECT", "DELETE", "INSERT", "UPDATE"):
        pat = "f[" + chr(39) + chr(34) + chr(39) + "].*" + kw + ".*" + ob
        matches = re.findall(pat, src)
        assert not matches, f"SQL f-string interpolation: {matches}"
