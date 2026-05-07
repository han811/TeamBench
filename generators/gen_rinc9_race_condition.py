"""
Parameterized generator for RINC9: Race Condition / TOCTOU Bug.

Inspiration: Therac-25 radiation overdose (1985-1987) — race condition
in concurrent state machine. More recently: TOCTOU bugs in file systems,
double-spend in payment systems, duplicate action bugs in web apps.

Seeds vary: race type (file TOCTOU / DB double-spend / API idempotency),
service name, resource being contested.

Grading: 7 checks — race condition fixed, atomicity preserved, concurrent
requests don't cause double-processing, correct final state.
"""
from __future__ import annotations

from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom

RACE_VARIANTS = [
    {
        "race_type": "double_spend",
        "service": "WalletService",
        "description": "concurrent balance check + debit without locking — allows balance to go negative",
        "fix": "use database-level row lock (SELECT FOR UPDATE) or optimistic locking with version check",
        "resource": "wallet balance",
        "operation": "debit",
    },
    {
        "race_type": "file_toctou",
        "service": "FileProcessorService",
        "description": "TOCTOU: check file existence then open — another process can delete between check and open",
        "fix": "use atomic open-with-exclusive-lock (fcntl.flock) or rely on exception handling instead of existence check",
        "resource": "file processing claim",
        "operation": "process_file",
    },
    {
        "race_type": "idempotency_missing",
        "service": "PaymentService",
        "description": "duplicate payment submission without idempotency key — same payment processed twice",
        "fix": "add idempotency_key to payment table; use INSERT OR IGNORE or upsert to deduplicate",
        "resource": "payment record",
        "operation": "submit_payment",
    },
]


class Generator(TaskGenerator):
    task_id = "RINC9_race_condition"
    domain = "incident"
    difficulty = "hard"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        v = RACE_VARIANTS[seed % len(RACE_VARIANTS)]
        initial_balance = rng.randint(100, 500)
        debit_amount = rng.randint(10, 50)
        n_concurrent = rng.choice([5, 10, 20])

        workspace_files = {
            "service.py": self._gen_service(v, initial_balance, debit_amount),
            "test_race.py": self._gen_tests(v, initial_balance, debit_amount, n_concurrent),
            "requirements.txt": "pytest>=7.0\n",
        }

        expected = {
            "seed": seed,
            "race_type": v["race_type"],
            "service": v["service"],
            "fix": v["fix"],
            "initial_balance": initial_balance,
            "debit_amount": debit_amount,
            "n_concurrent": n_concurrent,
        }

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=self._gen_spec(v, initial_balance, debit_amount, n_concurrent),
            brief_md=self._gen_brief(v),
            expected=expected,
            workspace_files=workspace_files,
            metadata={"difficulty": "hard", "category": "incident", "incident": "Therac-25-pattern"},
        )

    def _gen_service(self, v: dict, initial_balance: int, debit_amount: int) -> str:
        if v["race_type"] == "double_spend":
            return self._gen_wallet_service(v, initial_balance, debit_amount)
        elif v["race_type"] == "file_toctou":
            return self._gen_file_service(v)
        else:
            return self._gen_payment_service(v, initial_balance)

    def _gen_wallet_service(self, v: dict, initial_balance: int, debit_amount: int) -> str:
        return f'''\
"""
{v["service"]}: Wallet balance management.

RACE CONDITION: Check-then-act on balance without locking.
Two concurrent threads can both read balance=100, both pass the
check for debit={debit_amount}, both debit — final balance = 100 - 2*{debit_amount}.

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
        VALUES ('user_wallet', {initial_balance}, 0)
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
        return {{"success": False, "reason": "insufficient funds", "balance": balance}}
    time.sleep(0.001)  # simulate processing delay — makes race more likely
    conn.execute(
        "UPDATE wallets SET balance = balance - ? WHERE wallet_id = ?",
        (amount, wallet_id),
    )
    conn.commit()
    new_balance = get_balance(conn, wallet_id)
    return {{"success": True, "debited": amount, "new_balance": new_balance}}


def wallet_stats(conn, wallet_id: str) -> dict:
    row = conn.execute(
        "SELECT * FROM wallets WHERE wallet_id = ?", (wallet_id,)
    ).fetchone()
    return dict(row) if row else {{}}
'''

    def _gen_file_service(self, v: dict) -> str:
        return f'''\
"""
{v["service"]}: Claims and processes files from a work directory.

RACE CONDITION (TOCTOU): Checks if file exists, then opens it.
Between os.path.exists() and open(), another worker can claim and
delete the same file — causing FileNotFoundError or double-processing.

Inspiration: Distributed work queue TOCTOU bugs in file-based systems.
"""
import os
import fcntl
import threading
import time

WORK_DIR = "work_files"


def setup_work_dir(n_files: int = 10):
    os.makedirs(WORK_DIR, exist_ok=True)
    for i in range(n_files):
        path = os.path.join(WORK_DIR, f"task_{{i:04d}}.json")
        if not os.path.exists(path):
            with open(path, "w") as f:
                f.write(f'{{"task_id": {{i}}, "status": "pending"}}')


def claim_and_process(worker_id: str) -> dict:
    """Find an unclaimed file, mark it as in-progress, and process it.

    RACE CONDITION: os.path.exists() check + rename is not atomic.
    Two workers can both see the same file, both pass the exists check,
    then both try to rename/process it.

    Fix: use os.rename() atomically (POSIX atomic) or open with O_EXCL flag.
    """
    files = sorted(os.listdir(WORK_DIR)) if os.path.isdir(WORK_DIR) else []
    for fname in files:
        if not fname.endswith(".json"):
            continue
        src = os.path.join(WORK_DIR, fname)
        dst = os.path.join(WORK_DIR, fname.replace(".json", f".{{worker_id}}.processing"))

        # RACE CONDITION: another worker may claim src between exists() and rename()
        if os.path.exists(src):
            time.sleep(0.001)  # simulate delay — amplifies race
            try:
                os.rename(src, dst)
                # Successfully claimed — process it
                with open(dst) as f:
                    content = f.read()
                os.remove(dst)
                return {{"worker": worker_id, "claimed": fname, "content": content}}
            except (FileNotFoundError, OSError):
                continue  # already claimed by another worker
    return {{"worker": worker_id, "claimed": None}}


def count_remaining_files() -> int:
    if not os.path.isdir(WORK_DIR):
        return 0
    return len([f for f in os.listdir(WORK_DIR) if f.endswith(".json")])


def count_processing_files() -> int:
    if not os.path.isdir(WORK_DIR):
        return 0
    return len([f for f in os.listdir(WORK_DIR) if ".processing" in f])
'''

    def _gen_payment_service(self, v: dict, initial_balance: int) -> str:
        return f'''\
"""
{v["service"]}: Payment submission with idempotency.

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
        ({initial_balance},),
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

    return {{
        "payment_id": cursor.lastrowid,
        "payment_ref": payment_ref,
        "amount": amount,
        "new_balance": balance,
    }}


def count_payments(conn, payment_ref: str) -> int:
    return conn.execute(
        "SELECT COUNT(*) FROM payments WHERE payment_ref = ?", (payment_ref,)
    ).fetchone()[0]


def get_balance(conn, account_id: str) -> float:
    row = conn.execute(
        "SELECT balance FROM accounts WHERE account_id = ?", (account_id,)
    ).fetchone()
    return row["balance"] if row else 0.0
'''

    def _gen_tests(self, v: dict, initial_balance: int, debit_amount: int, n_concurrent: int) -> str:
        if v["race_type"] == "double_spend":
            return self._gen_wallet_tests(v, initial_balance, debit_amount, n_concurrent)
        elif v["race_type"] == "file_toctou":
            return self._gen_file_tests(v, n_concurrent)
        else:
            return self._gen_payment_tests(v, initial_balance, debit_amount, n_concurrent)

    def _gen_wallet_tests(self, v: dict, initial_balance: int, debit_amount: int, n_concurrent: int) -> str:
        max_debits = initial_balance // debit_amount
        return f'''\
"""Race condition tests for {v["service"]} — double spend."""
import threading
import pytest
import service as svc


@pytest.fixture
def conn():
    c = svc._get_conn()
    svc.setup_db(c)
    yield c
    c.close()


def test_single_debit_works(conn):
    result = svc.debit(conn, "user_wallet", {debit_amount})
    assert result["success"] is True
    assert result["new_balance"] == {initial_balance} - {debit_amount}


def test_insufficient_funds_rejected(conn):
    result = svc.debit(conn, "user_wallet", {initial_balance} + 1000)
    assert result["success"] is False
    assert "insufficient" in result["reason"]


def test_concurrent_debits_no_negative_balance(conn):
    """Concurrent debits must not drive balance below zero."""
    results = []
    errors = []
    lock = threading.Lock()

    def do_debit():
        try:
            # Each thread gets its own connection to simulate real concurrency
            c = svc._get_conn()
            r = svc.debit(c, "user_wallet", {debit_amount})
            with lock:
                results.append(r)
        except Exception as e:
            with lock:
                errors.append(str(e))

    threads = [threading.Thread(target=do_debit) for _ in range({n_concurrent})]
    for t in threads: t.start()
    for t in threads: t.join()

    # Check final balance
    final = svc.get_balance(conn, "user_wallet")
    assert final >= 0, (
        f"Balance went negative: {{final}} — race condition in debit()"
    )

    # Number of successful debits must match actual balance decrease
    initial = {initial_balance}
    successful = sum(1 for r in results if r.get("success"))
    expected_balance = initial - successful * {debit_amount}
    assert abs(final - expected_balance) < 0.01, (
        f"Balance mismatch: expected {{expected_balance}}, got {{final}} "
        f"({{successful}} successful debits)"
    )
'''

    def _gen_file_tests(self, v: dict, n_concurrent: int) -> str:
        return f'''\
"""Race condition tests for {v["service"]} — file TOCTOU."""
import os
import shutil
import threading
import pytest
import service as svc

WORK_DIR = svc.WORK_DIR


@pytest.fixture(autouse=True)
def setup_and_teardown():
    if os.path.isdir(WORK_DIR):
        shutil.rmtree(WORK_DIR)
    svc.setup_work_dir(n_files=20)
    yield
    if os.path.isdir(WORK_DIR):
        shutil.rmtree(WORK_DIR)


def test_single_worker_claims_file():
    result = svc.claim_and_process("worker_0")
    assert result["claimed"] is not None


def test_concurrent_workers_no_double_processing():
    """Each file must be processed by exactly one worker."""
    claimed = []
    lock = threading.Lock()

    def work(worker_id):
        while True:
            result = svc.claim_and_process(worker_id)
            if result["claimed"] is None:
                break
            with lock:
                claimed.append(result["claimed"])

    threads = [threading.Thread(target=work, args=(f"w{{i}}",)) for i in range({n_concurrent})]
    for t in threads: t.start()
    for t in threads: t.join()

    # Each filename should appear at most once
    unique = set(claimed)
    assert len(claimed) == len(unique), (
        f"Double processing detected: {{len(claimed)}} claims, {{len(unique)}} unique files"
    )


def test_all_files_processed():
    """All files must eventually be claimed (no starvation)."""
    initial_count = svc.count_remaining_files()
    claimed = []
    lock = threading.Lock()

    def work(worker_id):
        while True:
            result = svc.claim_and_process(worker_id)
            if result["claimed"] is None:
                break
            with lock:
                claimed.append(result["claimed"])

    threads = [threading.Thread(target=work, args=(f"w{{i}}",)) for i in range(4)]
    for t in threads: t.start()
    for t in threads: t.join()

    assert len(claimed) == initial_count, (
        f"Not all files processed: {{len(claimed)}}/{{initial_count}}"
    )
    assert svc.count_remaining_files() == 0
    assert svc.count_processing_files() == 0
'''

    def _gen_payment_tests(self, v: dict, initial_balance: int, debit_amount: int, n_concurrent: int) -> str:
        return f'''\
"""Race condition tests for {v["service"]} — duplicate payment."""
import threading
import pytest
import service as svc


@pytest.fixture
def conn():
    c = svc._get_conn()
    svc.setup_db(c)
    yield c
    c.close()


def test_single_payment_works(conn):
    result = svc.submit_payment(conn, "pay_001", {debit_amount}, "acc_001")
    assert result["payment_ref"] == "pay_001"
    assert result["amount"] == {debit_amount}


def test_duplicate_payment_processed_once(conn):
    """Submitting same payment_ref twice must only debit once."""
    svc.submit_payment(conn, "pay_idempotent", {debit_amount}, "acc_001")
    try:
        svc.submit_payment(conn, "pay_idempotent", {debit_amount}, "acc_001")
    except Exception:
        pass  # Duplicate rejection via exception is acceptable

    count = svc.count_payments(conn, "pay_idempotent")
    assert count == 1, (
        f"Duplicate payment_ref processed {{count}} times — missing idempotency"
    )
    # Balance should only be debited once
    balance = svc.get_balance(conn, "acc_001")
    assert balance == {initial_balance} - {debit_amount}, (
        f"Balance debited {{({initial_balance} - balance) / {debit_amount}:.0f}} times instead of 1"
    )


def test_concurrent_duplicate_payments_processed_once(conn):
    """Concurrent submissions of same payment_ref must debit only once."""
    results = []
    errors = []
    lock = threading.Lock()

    def submit():
        try:
            c = svc._get_conn()
            svc.setup_db(c)
            # All threads share the same payment_ref
            r = svc.submit_payment(c, "pay_concurrent", {debit_amount}, "acc_001")
            with lock:
                results.append(r)
        except Exception as e:
            with lock:
                errors.append(str(e))

    threads = [threading.Thread(target=submit) for _ in range({n_concurrent})]
    for t in threads: t.start()
    for t in threads: t.join()

    # Only one payment should have been processed
    count = svc.count_payments(conn, "pay_concurrent")
    assert count <= 1, (
        f"Concurrent duplicate: payment processed {{count}} times"
    )


def test_different_payment_refs_independent(conn):
    """Different payment_refs must each be processed independently."""
    for i in range(5):
        svc.submit_payment(conn, f"pay_{{i}}", 1.0, "acc_001")
    assert svc.get_balance(conn, "acc_001") == {initial_balance} - 5.0
'''

    def _gen_spec(self, v: dict, initial_balance: int, debit_amount: int, n_concurrent: int) -> str:
        return f"""# RINC9: Race Condition — {v["race_type"].replace("_", " ").title()}

## Incident Background
Race condition bugs have caused catastrophic failures ranging from the Therac-25
radiation overdose incidents (1985-1987) to modern payment double-charge bugs.
The common pattern: read state, make decision, act — without atomic guarantees.

## Service: {v["service"]}
File: `service.py`

## Problem
{v["description"]}

**Timing window:** Under concurrent load with {n_concurrent} threads,
the race window (read-check-write gap) is exploited reliably.

## Required Fix
{v["fix"]}

The fix must ensure atomicity — the check and the action must happen
as a single atomic unit that no other thread can interleave.

## Acceptance Criteria
1. Concurrent {v["operation"]} calls do not produce inconsistent state
2. Single {v["operation"]} still works correctly
3. Invalid operations are still rejected
4. No deadlocks under concurrent load
5. Final state is consistent with the number of successful operations
6. All tests pass: `pytest test_race.py -v`

## Files
- `service.py` — fix the race condition
- `test_race.py` — do NOT modify
"""

    def _gen_brief(self, v: dict) -> str:
        return f"""# RINC9: Race Condition Fix (Brief)

The {v["service"]} has a concurrency bug — {v["resource"]} is being
corrupted under concurrent load.

Fix the race condition in `service.py`.

Verify with:
```
pytest test_race.py -v
```

**Files to fix:** `service.py`
**Do NOT modify:** `test_race.py`
"""
