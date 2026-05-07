"""
BookstoreAPI: REST API for bookstore management.

WARNING: This code contains SQL injection vulnerabilities for training purposes.
Inspiration: OWASP Top 10 A03:2021 — Injection
"""
import sqlite3
import os
from flask import Flask, request, jsonify, g

app = Flask(__name__)
app.config["SECRET_KEY"] = "dev-secret-7890"
DATABASE = "bookstore.db"


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
def search_books():
    """Search books by title.

    VULNERABLE: unsanitized query parameter interpolated into SQL string.
    An attacker can inject SQL via the ?q= parameter.
    """
    query = request.args.get("q", "")
    db = get_db()
    # VULNERABILITY: direct string interpolation — never do this
    sql = f"SELECT * FROM books WHERE title LIKE " + "'%" + "{query}" + "%'"
    rows = db.execute(sql).fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/book/<item_id>")
def get_book(item_id):
    """Get a single book by ID.

    VULNERABLE: item_id from URL path directly interpolated into SQL.
    """
    db = get_db()
    # VULNERABILITY: item_id is user-controlled input
    sql = f"SELECT * FROM books WHERE book_id = {item_id}"
    row = db.execute(sql).fetchone()
    if row is None:
        return jsonify({"error": "book not found"}), 404
    return jsonify(dict(row))


@app.route("/admin/delete/<item_id>", methods=["DELETE"])
def delete_book(item_id):
    """Delete a book by ID (admin endpoint).

    VULNERABLE: item_id directly interpolated into DELETE statement.
    """
    db = get_db()
    # VULNERABILITY: item_id is user-controlled — can delete all rows
    sql = f"DELETE FROM books WHERE book_id = {item_id}"
    db.execute(sql)
    db.commit()
    return jsonify({"deleted": item_id})


@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": "BookstoreAPI"})


if __name__ == "__main__":
    app.run(port=5050, debug=False)
