"""Race condition tests for PaymentService — duplicate payment."""
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
    result = svc.submit_payment(conn, "pay_001", 15, "acc_001")
    assert result["payment_ref"] == "pay_001"
    assert result["amount"] == 15


def test_duplicate_payment_processed_once(conn):
    """Submitting same payment_ref twice must only debit once."""
    svc.submit_payment(conn, "pay_idempotent", 15, "acc_001")
    try:
        svc.submit_payment(conn, "pay_idempotent", 15, "acc_001")
    except Exception:
        pass  # Duplicate rejection via exception is acceptable

    count = svc.count_payments(conn, "pay_idempotent")
    assert count == 1, (
        f"Duplicate payment_ref processed {count} times — missing idempotency"
    )
    # Balance should only be debited once
    balance = svc.get_balance(conn, "acc_001")
    assert balance == 128 - 15, (
        f"Balance debited {(128 - balance) / 15:.0f} times instead of 1"
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
            r = svc.submit_payment(c, "pay_concurrent", 15, "acc_001")
            with lock:
                results.append(r)
        except Exception as e:
            with lock:
                errors.append(str(e))

    threads = [threading.Thread(target=submit) for _ in range(5)]
    for t in threads: t.start()
    for t in threads: t.join()

    # Only one payment should have been processed
    count = svc.count_payments(conn, "pay_concurrent")
    assert count <= 1, (
        f"Concurrent duplicate: payment processed {count} times"
    )


def test_different_payment_refs_independent(conn):
    """Different payment_refs must each be processed independently."""
    for i in range(5):
        svc.submit_payment(conn, f"pay_{i}", 1.0, "acc_001")
    assert svc.get_balance(conn, "acc_001") == 128 - 5.0
