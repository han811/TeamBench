"""
EventBusService: Pub/sub event bus.

MEMORY LEAK: Listeners are registered but never deregistered.
Each time a component subscribes (e.g., on every HTTP request),
a new listener is added. The listener list grows without bound.

Incident pattern: React/Node.js EventEmitter memory warnings,
Python asyncio uncleaned callbacks.
"""
import threading
from typing import Callable, Optional


class EventBus:
    """Simple synchronous event bus.

    VULNERABLE: subscribe() adds listeners but there is no
    unsubscribe mechanism. Listener list grows forever.
    """

    def __init__(self):
        self._listeners: dict[str, list[Callable]] = {}
        self._lock = threading.Lock()
        self._event_counts: dict[str, int] = {}

    def subscribe(self, event: str, handler: Callable) -> None:
        """Register a handler for an event.

        LEAK: no return value for unsubscription, no max_listeners limit.
        Each call permanently adds to the listener list.
        Fix: return an unsubscribe token; add max_listeners=100 guard.
        """
        with self._lock:
            if event not in self._listeners:
                self._listeners[event] = []
            # LEAK: no eviction, no duplicate check, no limit
            self._listeners[event].append(handler)

    def publish(self, event: str, data: dict) -> int:
        """Publish an event to all registered handlers."""
        with self._lock:
            handlers = list(self._listeners.get(event, []))
            self._event_counts[event] = self._event_counts.get(event, 0) + 1
        called = 0
        for handler in handlers:
            try:
                handler(data)
                called += 1
            except Exception:
                pass
        return called

    def listener_count(self, event: str) -> int:
        with self._lock:
            return len(self._listeners.get(event, []))

    def stats(self) -> dict:
        with self._lock:
            return {
                "events": list(self._listeners.keys()),
                "listener_counts": {e: len(ls) for e, ls in self._listeners.items()},
                "total_listeners": sum(len(ls) for ls in self._listeners.values()),
                "max_size": 100,
            }


_bus = EventBus()


def get_bus() -> EventBus:
    return _bus


def reset_bus():
    global _bus
    _bus = EventBus()
