"""
PaymentService: Payment submission with idempotency.

RACE CONDITION: Duplicate payment submissions (network retry, double-click)
are not deduplicated — the same payment is processed twice.

Inspiration: Payment processor double-charge incidents.
The fix is an idempotency key: client sends a unique key per payment,
server rejects duplicates atomically.
"""
import sqlite3
import threading
import time

DB = ":memory:"


def _get_conn():
    conn = sqlite3.connect(DB, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def setup_db(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            payment_ref TEXT,
            amount REAL NOT NULL,
            status TEXT DEFAULT 'completed',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            account_id TEXT PRIMARY KEY,
            balance REAL NOT NULL
        )
    """)
    conn.execute(
        "INSERT OR REPLACE INTO accounts (account_id, balance) VALUES ('acc_001', ?)",
        (128,),
    )
    conn.commit()


def submit_payment(conn, payment_ref: str, amount: float, account_id: str) -> dict:
    """Submit a payment. Must be idempotent on payment_ref.

    VULNERABLE: no idempotency check — duplicate payment_ref processes twice.
    Fix: add UNIQUE constraint on payment_ref; use INSERT OR IGNORE.
    """
    time.sleep(0.001)  # simulate processing delay

    # VULNERABLE: no duplicate check before insert
    cursor = conn.execute(
        "INSERT INTO payments (payment_ref, amount) VALUES (?, ?)",
        (payment_ref, amount),
    )
    conn.execute(
        "UPDATE accounts SET balance = balance - ? WHERE account_id = ?",
        (amount, account_id),
    )
    conn.commit()

    balance = conn.execute(
        "SELECT balance FROM accounts WHERE account_id = ?", (account_id,)
    ).fetchone()["balance"]

    return {
        "payment_id": cursor.lastrowid,
        "payment_ref": payment_ref,
        "amount": amount,
        "new_balance": balance,
    }


def count_payments(conn, payment_ref: str) -> int:
    return conn.execute(
        "SELECT COUNT(*) FROM payments WHERE payment_ref = ?", (payment_ref,)
    ).fetchone()[0]


def get_balance(conn, account_id: str) -> float:
    row = conn.execute(
        "SELECT balance FROM accounts WHERE account_id = ?", (account_id,)
    ).fetchone()
    return row["balance"] if row else 0.0
