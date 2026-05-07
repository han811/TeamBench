"""
DatabasePoolService: Connection pool for database access.

MEMORY LEAK: Connections are acquired from the pool but not returned
on error paths. Pool exhausts; new requests block or fail.

Incident pattern: Common in pre-context-manager code where error handling
forgets to call conn.release() or conn.close().
"""
import threading
import time
from contextlib import contextmanager


class Connection:
    """Simulated database connection."""
    _id_counter = 0

    def __init__(self):
        Connection._id_counter += 1
        self.id = Connection._id_counter
        self.active = True

    def query(self, sql: str) -> list:
        if not self.active:
            raise RuntimeError("Connection already closed")
        time.sleep(0.001)
        return [{"sql": sql, "conn_id": self.id}]

    def close(self):
        self.active = False


class ConnectionPool:
    """Pool of database connections."""

    def __init__(self, max_connections: int = 100):
        self.max_connections = max_connections
        self._pool: list[Connection] = [Connection() for _ in range(max_connections)]
        self._in_use: list[Connection] = []
        self._lock = threading.Lock()

    def acquire(self) -> Connection:
        with self._lock:
            if not self._pool:
                raise RuntimeError(f"Connection pool exhausted ({len(self._in_use)} in use)")
            conn = self._pool.pop()
            self._in_use.append(conn)
            return conn

    def release(self, conn: Connection):
        with self._lock:
            if conn in self._in_use:
                self._in_use.remove(conn)
                self._pool.append(conn)

    def stats(self) -> dict:
        with self._lock:
            return {
                "available": len(self._pool),
                "in_use": len(self._in_use),
                "max": self.max_connections,
            }


# Global pool
_pool = ConnectionPool(max_connections=100)


def execute_query(sql: str) -> list:
    """Execute a SQL query using a pooled connection.

    VULNERABLE: connection not released on exception path.
    After enough errors, pool exhausts and all queries fail.
    Fix: use a context manager or try/finally to guarantee release.
    """
    conn = _pool.acquire()
    # LEAK: if query raises, conn is never released back to pool
    results = conn.query(sql)
    _pool.release(conn)
    return results


def execute_query_with_error(sql: str) -> list:
    """Execute a query that always raises — demonstrates the leak."""
    conn = _pool.acquire()
    # LEAK: exception prevents release
    raise RuntimeError(f"Query failed: {sql}")
    _pool.release(conn)  # never reached
    return []


def pool_stats() -> dict:
    return _pool.stats()


def reset_pool():
    """Reset pool for testing."""
    global _pool
    _pool = ConnectionPool(max_connections=100)
