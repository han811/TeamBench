"""
UserAPI: REST API for users management.

WARNING: This code contains SQL injection vulnerabilities for training purposes.
Inspiration: OWASP Top 10 A03:2021 — Injection
"""
import sqlite3
import os
from flask import Flask, request, jsonify, g

app = Flask(__name__)
app.config["SECRET_KEY"] = "dev-secret-2500"
DATABASE = "users.db"


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


@app.route("/search")
def search_users():
    """Search users by username.

    VULNERABLE: unsanitized query parameter interpolated into SQL string.
    An attacker can inject SQL via the ?q= parameter.
    """
    query = request.args.get("q", "")
    db = get_db()
    # VULNERABILITY: direct string interpolation — never do this
    sql = f"SELECT * FROM users WHERE username LIKE " + "'%" + "{query}" + "%'"
    rows = db.execute(sql).fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/user/<item_id>")
def get_user(item_id):
    """Get a single user by ID.

    VULNERABLE: item_id from URL path directly interpolated into SQL.
    """
    db = get_db()
    # VULNERABILITY: item_id is user-controlled input
    sql = f"SELECT * FROM users WHERE user_id = {item_id}"
    row = db.execute(sql).fetchone()
    if row is None:
        return jsonify({"error": "user not found"}), 404
    return jsonify(dict(row))


@app.route("/admin/delete/<item_id>", methods=["DELETE"])
def delete_user(item_id):
    """Delete a user by ID (admin endpoint).

    VULNERABLE: item_id directly interpolated into DELETE statement.
    """
    db = get_db()
    # VULNERABILITY: item_id is user-controlled — can delete all rows
    sql = f"DELETE FROM users WHERE user_id = {item_id}"
    db.execute(sql)
    db.commit()
    return jsonify({"deleted": item_id})


@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": "UserAPI"})


if __name__ == "__main__":
    app.run(port=5008, debug=False)
