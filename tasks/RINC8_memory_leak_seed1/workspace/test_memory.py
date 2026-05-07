"""Memory/resource leak tests for DatabasePoolService — connection pool."""
import pytest
import service as svc


@pytest.fixture(autouse=True)
def reset():
    svc.reset_pool()
    yield
    svc.reset_pool()


def test_normal_query_works():
    result = svc.execute_query("SELECT 1")
    assert isinstance(result, list)


def test_connection_released_after_success():
    """After a successful query, connection must return to pool."""
    before = svc.pool_stats()["available"]
    svc.execute_query("SELECT 1")
    after = svc.pool_stats()["available"]
    assert after == before, (
        f"Connection not released: available went {before} → {after}"
    )


def test_connection_released_after_error():
    """Even if query raises, connection must return to pool."""
    before = svc.pool_stats()["available"]
    try:
        svc.execute_query_with_error("SELECT fail")
    except RuntimeError:
        pass
    after = svc.pool_stats()["available"]
    assert after == before, (
        f"Connection leaked on error: available went {before} → {after} — use try/finally"
    )


def test_pool_not_exhausted_after_repeated_errors():
    """Repeated failed queries must not exhaust the pool."""
    for _ in range(100 + 5):
        try:
            svc.execute_query_with_error("SELECT fail")
        except Exception:
            pass
    stats = svc.pool_stats()
    assert stats["available"] > 0, (
        f"Pool exhausted: {stats['available']} available — connection leak on error path"
    )


def test_concurrent_queries_succeed():
    """Concurrent queries must all get connections and release them."""
    import threading
    errors = []
    def do_query():
        try:
            svc.execute_query("SELECT 1")
        except Exception as e:
            errors.append(str(e))
    threads = [threading.Thread(target=do_query) for _ in range(min(100//2, 10))]
    for t in threads: t.start()
    for t in threads: t.join()
    assert not errors, f"Concurrent queries failed: {errors}"
