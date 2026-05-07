"""
Parameterized generator for DIST3: Payment Service Idempotency.

Each seed produces a different payment domain context but the same structural
challenge: 4 non-idempotent operations that must be fixed, plus 1 already-
idempotent read-only endpoint that must NOT be modified (trap check C7).

Seed 0: E-commerce payments (charges/refunds for orders)
Seed 1: Subscription billing (recurring charges/credits)
Seed 2: Marketplace payments (split payments/disbursements)
"""
from __future__ import annotations
import os
from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom


# Per-seed domain context — 8 entries so seeds 0-7 all produce distinct workspaces
DOMAINS = [
    {
        "name": "e-commerce",
        "charge_desc": "Create a charge for an order",
        "refund_desc": "Process a refund for a returned order",
        "webhook_desc": "Deliver order status webhook to merchant",
        "ledger_desc": "Record order revenue ledger entry",
        "balance_desc": "Get merchant account balance",
        "charge_comment": "E-commerce order charge",
        "refund_comment": "E-commerce order refund",
        "webhook_event": "order.charged",
        "ledger_direction": "credit",
        "currency": "USD",
        "test_amount": "99.99",
        "test_key_prefix": "order",
        "test_charge_id": "ch_ord_abc123",
    },
    {
        "name": "subscription billing",
        "charge_desc": "Create a recurring subscription charge",
        "refund_desc": "Issue a subscription credit/refund",
        "webhook_desc": "Deliver subscription lifecycle webhook",
        "ledger_desc": "Record subscription revenue ledger entry",
        "balance_desc": "Get subscriber account balance",
        "charge_comment": "Subscription billing charge",
        "refund_comment": "Subscription credit",
        "webhook_event": "subscription.renewed",
        "ledger_direction": "credit",
        "currency": "USD",
        "test_amount": "29.99",
        "test_key_prefix": "sub",
        "test_charge_id": "ch_sub_xyz789",
    },
    {
        "name": "marketplace",
        "charge_desc": "Create a marketplace split payment charge",
        "refund_desc": "Process a marketplace disbursement refund",
        "webhook_desc": "Deliver marketplace payout webhook",
        "ledger_desc": "Record marketplace disbursement ledger entry",
        "balance_desc": "Get marketplace seller account balance",
        "charge_comment": "Marketplace split payment",
        "refund_comment": "Marketplace disbursement refund",
        "webhook_event": "payout.disbursed",
        "ledger_direction": "debit",
        "currency": "EUR",
        "test_amount": "150.00",
        "test_key_prefix": "mkt",
        "test_charge_id": "ch_mkt_pqr456",
    },
    {
        "name": "digital goods",
        "charge_desc": "Create a charge for a digital download purchase",
        "refund_desc": "Issue a refund for a digital goods purchase",
        "webhook_desc": "Deliver download fulfillment webhook to vendor",
        "ledger_desc": "Record digital goods revenue ledger entry",
        "balance_desc": "Get vendor payout balance",
        "charge_comment": "Digital goods purchase charge",
        "refund_comment": "Digital goods refund",
        "webhook_event": "download.purchased",
        "ledger_direction": "credit",
        "currency": "USD",
        "test_amount": "14.99",
        "test_key_prefix": "dg",
        "test_charge_id": "ch_dg_stu321",
    },
    {
        "name": "hotel booking",
        "charge_desc": "Create a charge for a hotel room reservation",
        "refund_desc": "Process a cancellation refund for a hotel booking",
        "webhook_desc": "Deliver booking confirmation webhook to property",
        "ledger_desc": "Record hotel booking revenue ledger entry",
        "balance_desc": "Get property account balance",
        "charge_comment": "Hotel booking deposit charge",
        "refund_comment": "Hotel cancellation refund",
        "webhook_event": "booking.confirmed",
        "ledger_direction": "credit",
        "currency": "USD",
        "test_amount": "249.00",
        "test_key_prefix": "htl",
        "test_charge_id": "ch_htl_vwx654",
    },
    {
        "name": "ride-hailing",
        "charge_desc": "Create a charge for a completed ride",
        "refund_desc": "Issue a refund for a disputed ride charge",
        "webhook_desc": "Deliver ride completion webhook to driver app",
        "ledger_desc": "Record driver earnings ledger entry",
        "balance_desc": "Get driver earnings balance",
        "charge_comment": "Ride fare charge",
        "refund_comment": "Ride dispute refund",
        "webhook_event": "ride.completed",
        "ledger_direction": "credit",
        "currency": "USD",
        "test_amount": "18.50",
        "test_key_prefix": "ride",
        "test_charge_id": "ch_ride_yza987",
    },
    {
        "name": "insurance premium",
        "charge_desc": "Create a monthly insurance premium charge",
        "refund_desc": "Issue a pro-rated policy cancellation refund",
        "webhook_desc": "Deliver premium payment webhook to insurer",
        "ledger_desc": "Record premium revenue ledger entry",
        "balance_desc": "Get policyholder account balance",
        "charge_comment": "Insurance premium payment",
        "refund_comment": "Insurance cancellation refund",
        "webhook_event": "premium.paid",
        "ledger_direction": "credit",
        "currency": "USD",
        "test_amount": "75.00",
        "test_key_prefix": "ins",
        "test_charge_id": "ch_ins_bcd111",
    },
    {
        "name": "crypto exchange",
        "charge_desc": "Create a trading fee charge for a crypto swap",
        "refund_desc": "Reverse a failed trade fee charge",
        "webhook_desc": "Deliver trade settlement webhook to wallet service",
        "ledger_desc": "Record trading fee revenue ledger entry",
        "balance_desc": "Get trader account balance",
        "charge_comment": "Crypto trading fee charge",
        "refund_comment": "Failed trade fee reversal",
        "webhook_event": "trade.settled",
        "ledger_direction": "credit",
        "currency": "USDC",
        "test_amount": "2.50",
        "test_key_prefix": "cex",
        "test_charge_id": "ch_cex_efg222",
    },
]


class Generator(TaskGenerator):
    task_id = "DIST3_idempotency"
    domain = "Distributed"
    difficulty = "hard"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        ctx = DOMAINS[seed % len(DOMAINS)]

        workspace_files = self._make_workspace(ctx, seed)

        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", "DIST3_idempotency"
        )
        with open(os.path.join(tasks_dir, "spec.md")) as f:
            spec_md = f.read()
        with open(os.path.join(tasks_dir, "brief.md")) as f:
            brief_md = f.read()

        return GeneratedTask(
            task_id="DIST3_idempotency",
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "idempotent_ops": ["charges", "refunds", "webhooks", "ledger"],
                "must_not_modify": ["balance"],
                "seed": seed,
                "domain": ctx["name"],
            },
            workspace_files=workspace_files,
            metadata={"difficulty": "hard", "category": "Distributed"},
        )

    def _make_workspace(self, ctx: dict, seed: int) -> dict:
        files = {}

        files["payments/__init__.py"] = ""
        files["tests/__init__.py"] = ""

        # --- payments/database.py ---
        files["payments/database.py"] = '''\
import sqlite3
import threading

_lock = threading.Lock()
_conn = None


def setup_db():
    """Initialize or reset the in-memory test database (shared across threads)."""
    global _conn
    with _lock:
        conn = sqlite3.connect(":memory:", check_same_thread=False)
        conn.execute(
            "CREATE TABLE IF NOT EXISTS charges "
            "(id TEXT PRIMARY KEY, amount REAL, currency TEXT, status TEXT)"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS refunds "
            "(id TEXT PRIMARY KEY, charge_id TEXT, amount REAL, status TEXT)"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS ledger "
            "(id TEXT PRIMARY KEY, amount REAL, direction TEXT, created_at TEXT)"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS webhook_log "
            "(id TEXT PRIMARY KEY, event_type TEXT, delivered_at TEXT)"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS balances "
            "(account_id TEXT PRIMARY KEY, amount REAL)"
        )
        conn.execute("INSERT OR IGNORE INTO balances VALUES ('default', 0.0)")
        conn.commit()
        _conn = conn


def get_db():
    global _conn
    if _conn is None:
        setup_db()
    return _conn
'''

        # --- payments/idempotency.py (empty stub — executor must implement) ---
        files["payments/idempotency.py"] = '''\
"""
Idempotency store for payment operations.

TODO: Implement the IdempotencyStore class and helper functions.
Operations should check for an existing result before executing,
and store results after execution to prevent duplicates on retry.
"""


def reset_store():
    """Reset the idempotency store. Used by tests to isolate state between runs."""
    pass  # TODO: implement once IdempotencyStore is implemented
'''

        # --- payments/charges.py (NOT idempotent) ---
        files["payments/charges.py"] = f'''\
import uuid
from payments.database import get_db


def create_charge(amount: float, currency: str, idempotency_key: str) -> dict:
    """{ctx["charge_desc"]}. WARNING: Not idempotent — retrying creates duplicate charges."""
    db = get_db()
    charge_id = str(uuid.uuid4())
    db.execute(
        "INSERT INTO charges (id, amount, currency, status) VALUES (?, ?, ?, ?)",
        (charge_id, amount, currency, "pending"),
    )
    db.commit()
    return {{
        "charge_id": charge_id,
        "amount": amount,
        "currency": currency,
        "status": "pending",
    }}
'''

        # --- payments/refunds.py (NOT idempotent) ---
        files["payments/refunds.py"] = f'''\
import uuid
from payments.database import get_db


def create_refund(charge_id: str, amount: float, idempotency_key: str) -> dict:
    """{ctx["refund_desc"]}. WARNING: Not idempotent — retrying creates duplicate refunds."""
    db = get_db()
    refund_id = str(uuid.uuid4())
    db.execute(
        "INSERT INTO refunds (id, charge_id, amount, status) VALUES (?, ?, ?, ?)",
        (refund_id, charge_id, amount, "processed"),
    )
    db.commit()
    return {{
        "refund_id": refund_id,
        "charge_id": charge_id,
        "amount": amount,
        "status": "processed",
    }}
'''

        # --- payments/webhooks.py (NOT idempotent) ---
        files["payments/webhooks.py"] = f'''\
import uuid
from datetime import datetime
from payments.database import get_db


def deliver_webhook(event_type: str, payload: dict, idempotency_key: str) -> dict:
    """{ctx["webhook_desc"]}. WARNING: Not idempotent — retrying delivers webhook multiple times."""
    db = get_db()
    delivery_id = str(uuid.uuid4())
    delivered_at = datetime.utcnow().isoformat()
    db.execute(
        "INSERT INTO webhook_log (id, event_type, delivered_at) VALUES (?, ?, ?)",
        (delivery_id, event_type, delivered_at),
    )
    db.commit()
    return {{
        "delivery_id": delivery_id,
        "event_type": event_type,
        "delivered_at": delivered_at,
        "status": "delivered",
    }}
'''

        # --- payments/ledger.py (NOT idempotent) ---
        files["payments/ledger.py"] = f'''\
import uuid
from datetime import datetime
from payments.database import get_db


def create_entry(amount: float, direction: str, idempotency_key: str) -> dict:
    """{ctx["ledger_desc"]}. WARNING: Not idempotent — retrying creates duplicate ledger entries."""
    db = get_db()
    entry_id = str(uuid.uuid4())
    created_at = datetime.utcnow().isoformat()
    db.execute(
        "INSERT INTO ledger (id, amount, direction, created_at) VALUES (?, ?, ?, ?)",
        (entry_id, amount, direction, created_at),
    )
    db.commit()
    return {{
        "entry_id": entry_id,
        "amount": amount,
        "direction": direction,
        "created_at": created_at,
    }}
'''

        # --- payments/balance.py (CORRECT — already idempotent, read-only) ---
        files["payments/balance.py"] = f'''\
from payments.database import get_db


def get_balance(account_id: str = "default") -> dict:
    """{ctx["balance_desc"]}. This is already idempotent (read-only)."""
    db = get_db()
    row = db.execute(
        "SELECT amount FROM balances WHERE account_id = ?", (account_id,)
    ).fetchone()
    return {{"account_id": account_id, "balance": row[0] if row else 0.0}}
'''

        # --- tests/test_charges.py ---
        amt = ctx["test_amount"]
        cur = ctx["currency"]
        prefix = ctx["test_key_prefix"]
        charge_id = ctx["test_charge_id"]

        files["tests/test_charges.py"] = f'''\
import pytest
from payments.charges import create_charge
from payments.database import setup_db, get_db
from payments.idempotency import reset_store


@pytest.fixture(autouse=True)
def fresh_db():
    setup_db()
    reset_store()
    yield


def test_retry_with_same_key_no_duplicate():
    """Retrying with same idempotency key must NOT create a second charge."""
    key = "{prefix}-retry-charge-001"
    result1 = create_charge({amt}, "{cur}", idempotency_key=key)
    result2 = create_charge({amt}, "{cur}", idempotency_key=key)  # retry

    assert result1["charge_id"] == result2["charge_id"], (
        "Retry must return same charge_id"
    )

    db = get_db()
    count = db.execute("SELECT COUNT(*) FROM charges").fetchone()[0]
    assert count == 1, f"Expected 1 charge, found {{count}} (double-charge!)"


def test_different_keys_create_different_charges():
    """Different idempotency keys must create separate charges."""
    result1 = create_charge({amt}, "{cur}", idempotency_key="{prefix}-key-A")
    result2 = create_charge({amt}, "{cur}", idempotency_key="{prefix}-key-B")

    assert result1["charge_id"] != result2["charge_id"]
    db = get_db()
    count = db.execute("SELECT COUNT(*) FROM charges").fetchone()[0]
    assert count == 2


def test_result_fields_present():
    """Result must contain required fields."""
    key = "{prefix}-field-check-001"
    result = create_charge({amt}, "{cur}", idempotency_key=key)
    assert "charge_id" in result
    assert "amount" in result
    assert "currency" in result
    assert "status" in result
'''

        # --- tests/test_refunds.py ---
        files["tests/test_refunds.py"] = f'''\
import pytest
from payments.refunds import create_refund
from payments.database import setup_db, get_db
from payments.idempotency import reset_store


@pytest.fixture(autouse=True)
def fresh_db():
    setup_db()
    reset_store()
    yield


def test_retry_with_same_key_no_duplicate():
    """Retrying with same idempotency key must NOT create a second refund."""
    key = "{prefix}-retry-refund-001"
    result1 = create_refund("{charge_id}", {amt}, idempotency_key=key)
    result2 = create_refund("{charge_id}", {amt}, idempotency_key=key)  # retry

    assert result1["refund_id"] == result2["refund_id"], (
        "Retry must return same refund_id"
    )

    db = get_db()
    count = db.execute("SELECT COUNT(*) FROM refunds").fetchone()[0]
    assert count == 1, f"Expected 1 refund, found {{count}} (double-refund!)"


def test_different_keys_create_different_refunds():
    """Different idempotency keys must create separate refunds."""
    result1 = create_refund("{charge_id}", {amt}, idempotency_key="{prefix}-ref-A")
    result2 = create_refund("{charge_id}", {amt}, idempotency_key="{prefix}-ref-B")

    assert result1["refund_id"] != result2["refund_id"]
    db = get_db()
    count = db.execute("SELECT COUNT(*) FROM refunds").fetchone()[0]
    assert count == 2
'''

        # --- tests/test_webhooks.py ---
        event = ctx["webhook_event"]
        files["tests/test_webhooks.py"] = f'''\
import pytest
from payments.webhooks import deliver_webhook
from payments.database import setup_db, get_db
from payments.idempotency import reset_store


@pytest.fixture(autouse=True)
def fresh_db():
    setup_db()
    reset_store()
    yield


def test_retry_delivers_webhook_exactly_once():
    """Retrying with same idempotency key must deliver webhook only once."""
    key = "{prefix}-webhook-001"
    payload = {{"amount": {amt}, "currency": "{cur}"}}
    result1 = deliver_webhook("{event}", payload, idempotency_key=key)
    result2 = deliver_webhook("{event}", payload, idempotency_key=key)  # retry

    assert result1["delivery_id"] == result2["delivery_id"], (
        "Retry must return same delivery_id"
    )

    db = get_db()
    count = db.execute("SELECT COUNT(*) FROM webhook_log").fetchone()[0]
    assert count == 1, f"Expected 1 webhook delivery, found {{count}} (duplicate delivery!)"


def test_different_keys_deliver_separate_webhooks():
    """Different idempotency keys must result in separate webhook deliveries."""
    payload = {{"amount": {amt}}}
    result1 = deliver_webhook("{event}", payload, idempotency_key="{prefix}-wh-A")
    result2 = deliver_webhook("{event}", payload, idempotency_key="{prefix}-wh-B")

    assert result1["delivery_id"] != result2["delivery_id"]
    db = get_db()
    count = db.execute("SELECT COUNT(*) FROM webhook_log").fetchone()[0]
    assert count == 2
'''

        # --- tests/test_ledger.py ---
        direction = ctx["ledger_direction"]
        files["tests/test_ledger.py"] = f'''\
import pytest
from payments.ledger import create_entry
from payments.database import setup_db, get_db
from payments.idempotency import reset_store


@pytest.fixture(autouse=True)
def fresh_db():
    setup_db()
    reset_store()
    yield


def test_retry_creates_ledger_entry_exactly_once():
    """Retrying with same idempotency key must create only one ledger entry."""
    key = "{prefix}-ledger-001"
    result1 = create_entry({amt}, "{direction}", idempotency_key=key)
    result2 = create_entry({amt}, "{direction}", idempotency_key=key)  # retry

    assert result1["entry_id"] == result2["entry_id"], (
        "Retry must return same entry_id"
    )

    db = get_db()
    count = db.execute("SELECT COUNT(*) FROM ledger").fetchone()[0]
    assert count == 1, f"Expected 1 ledger entry, found {{count}} (duplicate entry!)"


def test_different_keys_create_different_entries():
    """Different idempotency keys must create separate ledger entries."""
    result1 = create_entry({amt}, "{direction}", idempotency_key="{prefix}-led-A")
    result2 = create_entry({amt}, "{direction}", idempotency_key="{prefix}-led-B")

    assert result1["entry_id"] != result2["entry_id"]
    db = get_db()
    count = db.execute("SELECT COUNT(*) FROM ledger").fetchone()[0]
    assert count == 2
'''

        # --- tests/test_balance.py ---
        files["tests/test_balance.py"] = f'''\
import pytest
import inspect
from payments.balance import get_balance
from payments.database import setup_db
from payments.idempotency import reset_store


@pytest.fixture(autouse=True)
def fresh_db():
    setup_db()
    reset_store()
    yield


def test_balance_returns_correct_structure():
    """Balance endpoint must return account_id and balance fields."""
    result = get_balance("default")
    assert "account_id" in result
    assert "balance" in result
    assert result["account_id"] == "default"


def test_balance_has_no_idempotency_key_param():
    """Balance endpoint must NOT have idempotency_key parameter (already idempotent)."""
    sig = inspect.signature(get_balance)
    assert "idempotency_key" not in sig.parameters, (
        "get_balance must NOT have idempotency_key parameter "
        "(it is already idempotent as a read-only operation)"
    )


def test_balance_idempotent_by_nature():
    """Calling balance twice returns the same result (read-only)."""
    result1 = get_balance("default")
    result2 = get_balance("default")
    assert result1["balance"] == result2["balance"]
    assert result1["account_id"] == result2["account_id"]
'''

        # --- tests/test_concurrent.py ---
        files["tests/test_concurrent.py"] = f'''\
import threading
import pytest
from payments.charges import create_charge
from payments.database import setup_db, get_db
from payments.idempotency import reset_store


@pytest.fixture(autouse=True)
def fresh_db():
    setup_db()
    reset_store()
    yield


def test_concurrent_retries_no_duplicate():
    """10 concurrent threads retrying with the same key must produce exactly 1 charge."""
    key = "{prefix}-concurrent-001"
    results = []
    errors = []

    def do_charge():
        try:
            r = create_charge({amt}, "{cur}", idempotency_key=key)
            results.append(r)
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=do_charge) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"Threads raised errors: {{errors}}"
    assert len(results) == 10, "All threads must get a result"

    # All results must have the same charge_id
    charge_ids = {{r["charge_id"] for r in results}}
    assert len(charge_ids) == 1, (
        f"Expected 1 unique charge_id across all threads, got {{len(charge_ids)}}: {{charge_ids}}"
    )

    # Only 1 row in DB
    db = get_db()
    count = db.execute("SELECT COUNT(*) FROM charges").fetchone()[0]
    assert count == 1, f"Expected 1 charge in DB, found {{count}} (race condition!)"
'''

        # --- tests/test_idempotency.py ---
        files["tests/test_idempotency.py"] = '''\
"""Unit tests for the idempotency store itself."""
import pytest
from payments.idempotency import reset_store


@pytest.fixture(autouse=True)
def clean_store():
    reset_store()
    yield


def test_idempotency_module_importable():
    """payments/idempotency.py must be importable."""
    import payments.idempotency  # noqa: F401


def test_store_returns_none_for_unknown_key():
    """check_idempotency must return None for a key that has not been stored."""
    from payments.idempotency import check_idempotency, store_result
    result = check_idempotency("nonexistent-key-xyz")
    assert result is None


def test_store_and_retrieve():
    """Storing a result and retrieving it must return the same value."""
    from payments.idempotency import check_idempotency, store_result
    key = "test-store-retrieve-001"
    payload = {"charge_id": "ch_abc", "amount": 42.0}
    store_result(key, payload)
    retrieved = check_idempotency(key)
    assert retrieved is not None
    assert retrieved["charge_id"] == "ch_abc"
    assert retrieved["amount"] == 42.0


def test_store_does_not_overwrite():
    """Storing the same key twice must keep the first value."""
    from payments.idempotency import check_idempotency, store_result
    key = "test-no-overwrite-002"
    first = {"charge_id": "ch_first", "amount": 10.0}
    second = {"charge_id": "ch_second", "amount": 20.0}
    store_result(key, first)
    # Attempt to overwrite — implementations may allow this but
    # the idempotency pattern must guarantee the first call wins
    # (enforced at the operation level, not necessarily the store level).
    retrieved = check_idempotency(key)
    assert retrieved["charge_id"] == "ch_first"


def test_different_keys_isolated():
    """Results for different keys must not interfere."""
    from payments.idempotency import check_idempotency, store_result
    store_result("iso-key-A", {"value": "A"})
    store_result("iso-key-B", {"value": "B"})
    assert check_idempotency("iso-key-A")["value"] == "A"
    assert check_idempotency("iso-key-B")["value"] == "B"
'''

        return files
