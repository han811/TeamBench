# RINC1: SQL Injection Vulnerabilities

## Incident Background
Inspired by OWASP Top 10 A03:2021 — Injection. SQL injection remains the most
prevalent web vulnerability class. This task reproduces the pattern where
user-controlled input is interpolated directly into SQL query strings.

## Service: BookstoreAPI
File: `app.py` | Database: `bookstore.db`

## Vulnerabilities (3 locations)

### 1. Search endpoint — `/search?q=<input>`
```python
# VULNERABLE
sql = f"SELECT * FROM books WHERE title LIKE '%{query}%'"
```
Attack: `?q=' OR '1'='1` dumps all rows.

### 2. Get-by-ID endpoint — `/book/<item_id>`
```python
# VULNERABLE
sql = f"SELECT * FROM books WHERE book_id = {item_id}"
```
Attack: `//book/1 OR 1=1` bypasses ID lookup.

### 3. Delete endpoint — `/admin/delete/<item_id>` (DELETE)
```python
# VULNERABLE
sql = f"DELETE FROM books WHERE book_id = {item_id}"
```
Attack: `//admin/delete/1 OR 1=1` mass-deletes all rows.

## Required Fix: Parameterized Queries
Replace all three f-string SQL statements with parameterized queries using `?` placeholders:

```python
# SAFE
rows = db.execute(
    "SELECT * FROM books WHERE title LIKE ?", (f"%{query}%",)
).fetchall()
```

```python
row = db.execute(
    "SELECT * FROM books WHERE book_id = ?", (item_id,)
).fetchone()
```

```python
db.execute(
    "DELETE FROM books WHERE book_id = ?", (item_id,)
)
```

## Acceptance Criteria
1. `/search?q=' OR '1'='1` returns 0 rows (not all rows)
2. `/book/999 OR 1=1` returns 404 (not a valid row)
3. DELETE with injection payload does not delete more than 1 row
4. Normal search `/search?q=title_1` still returns results
5. Normal `/book/1` still returns the item
6. No f-string SQL interpolation remains in `app.py`
7. All tests pass: `pytest test_security.py -v`

## Files
- `app.py` — fix all 3 vulnerable SQL statements
- `init_db.py` — do NOT modify
- `test_security.py` — do NOT modify
