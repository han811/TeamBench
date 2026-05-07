"""Race condition tests for WalletService — double spend."""
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
    result = svc.debit(conn, "user_wallet", 36)
    assert result["success"] is True
    assert result["new_balance"] == 297 - 36


def test_insufficient_funds_rejected(conn):
    result = svc.debit(conn, "user_wallet", 297 + 1000)
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
            r = svc.debit(c, "user_wallet", 36)
            with lock:
                results.append(r)
        except Exception as e:
            with lock:
                errors.append(str(e))

    threads = [threading.Thread(target=do_debit) for _ in range(5)]
    for t in threads: t.start()
    for t in threads: t.join()

    # Check final balance
    final = svc.get_balance(conn, "user_wallet")
    assert final >= 0, (
        f"Balance went negative: {final} — race condition in debit()"
    )

    # Number of successful debits must match actual balance decrease
    initial = 297
    successful = sum(1 for r in results if r.get("success"))
    expected_balance = initial - successful * 36
    assert abs(final - expected_balance) < 0.01, (
        f"Balance mismatch: expected {expected_balance}, got {final} "
        f"({successful} successful debits)"
    )
