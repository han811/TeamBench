"""Memory leak tests for EventBusService — event listener accumulation."""
import pytest
import service as svc


@pytest.fixture(autouse=True)
def reset():
    svc.reset_bus()
    yield
    svc.reset_bus()


def test_publish_calls_listener():
    bus = svc.get_bus()
    received = []
    bus.subscribe("test_event", lambda d: received.append(d))
    bus.publish("test_event", {"msg": "hello"})
    assert received == [{"msg": "hello"}]


def test_listener_count_bounded():
    """Listener count must not grow beyond max_size."""
    bus = svc.get_bus()
    for i in range(246):
        bus.subscribe("load_event", lambda d: None)
    count = bus.listener_count("load_event")
    assert count <= 100, (
        f"Listener count {count} exceeds max_size 100 — listener leak detected"
    )


def test_unsubscribe_removes_listener():
    """subscribe() must return a token; calling it removes the listener."""
    bus = svc.get_bus()
    received = []
    token = bus.subscribe("unsub_event", lambda d: received.append(d))
    assert token is not None, "subscribe() must return an unsubscribe token"
    # Unsubscribe
    token()  # call the token to unsubscribe
    bus.publish("unsub_event", {"msg": "after unsub"})
    assert received == [], "Listener still called after unsubscribe"


def test_publish_after_all_unsub():
    """After all listeners unsubscribed, publish returns 0 calls."""
    bus = svc.get_bus()
    tokens = []
    for _ in range(5):
        tokens.append(bus.subscribe("cleanup_event", lambda d: None))
    for t in tokens:
        t()
    called = bus.publish("cleanup_event", {})
    assert called == 0, f"Listeners still firing after unsubscribe: called={called}"


def test_stats_reflect_listener_count():
    bus = svc.get_bus()
    bus.subscribe("stat_event", lambda d: None)
    bus.subscribe("stat_event", lambda d: None)
    stats = bus.stats()
    assert stats["listener_counts"].get("stat_event", 0) <= 100
