"""
WalletService: Wallet balance management.

RACE CONDITION: Check-then-act on balance without locking.
Two concurrent threads can both read balance=100, both pass the
check for debit=36, both debit — final balance = 100 - 2*36.

Inspiration: Double-spend attacks, payment processor race conditions.
"""
import sqlite3
import threading
import time

DB = ":memory:"
_db_lock = threading.Lock()  # exists but not used in vulnerable code


def _get_conn():
    conn = sqlite3.connect(DB, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def setup_db(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS wallets (
            wallet_id TEXT PRIMARY KEY,
            balance REAL NOT NULL,
            version INTEGER DEFAULT 0
        )
    """)
    conn.execute("""
        INSERT OR REPLACE INTO wallets (wallet_id, balance, version)
        VALUES ('user_wallet', 297, 0)
    """)
    conn.commit()


def get_balance(conn, wallet_id: str) -> float:
    row = conn.execute(
        "SELECT balance FROM wallets WHERE wallet_id = ?", (wallet_id,)
    ).fetchone()
    return row["balance"] if row else 0.0


def debit(conn, wallet_id: str, amount: float) -> dict:
    """Debit amount from wallet.

    RACE CONDITION (TOCTOU): reads balance, checks sufficiency, then updates.
    Between the read and the update, another thread can read the same balance.

    Fix: use atomic UPDATE with WHERE balance >= amount and check rows_affected,
    or acquire a row-level lock before the check.
    """
    # VULNERABLE: read-check-write without atomic lock
    balance = get_balance(conn, wallet_id)
    if balance < amount:
        return {"success": False, "reason": "insufficient funds", "balance": balance}
    time.sleep(0.001)  # simulate processing delay — makes race more likely
    conn.execute(
        "UPDATE wallets SET balance = balance - ? WHERE wallet_id = ?",
        (amount, wallet_id),
    )
    conn.commit()
    new_balance = get_balance(conn, wallet_id)
    return {"success": True, "debited": amount, "new_balance": new_balance}


def wallet_stats(conn, wallet_id: str) -> dict:
    row = conn.execute(
        "SELECT * FROM wallets WHERE wallet_id = ?", (wallet_id,)
    ).fetchone()
    return dict(row) if row else {}
