"""Memory leak tests for ProductCacheService — unbounded cache."""
import pytest
import importlib
import service as svc


@pytest.fixture(autouse=True)
def reset():
    svc.clear_cache()
    yield
    svc.clear_cache()


def test_cache_returns_correct_data():
    product = svc.get_product("prod_001")
    assert product["id"] == "prod_001"
    assert "name" in product


def test_cache_hit_on_second_request():
    svc.get_product("prod_hit_test")
    before = svc.cache_stats()["hits"]
    svc.get_product("prod_hit_test")
    assert svc.cache_stats()["hits"] > before


def test_cache_bounded_under_load():
    """Cache size must not exceed max_size after many unique requests."""
    for i in range(415):
        svc.get_product(f"unique_product_{i}")
    stats = svc.cache_stats()
    assert stats["size"] <= 500, (
        f"Cache size {stats['size']} exceeds max_size 500 — memory leak detected"
    )


def test_cache_evicts_old_entries():
    """When cache is full, old entries should be evicted (LRU)."""
    # Fill cache beyond max_size
    for i in range(500 + 50):
        svc.get_product(f"eviction_test_{i}")
    stats = svc.cache_stats()
    assert stats["size"] <= 500, (
        f"No eviction: cache size {stats['size']} after filling to 550"
    )


def test_memory_stable_across_repeated_requests():
    """Repeatedly requesting the same keys must not grow the cache."""
    for _ in range(3):
        for i in range(20):
            svc.get_product(f"stable_{i}")
    stats = svc.cache_stats()
    assert stats["size"] <= 20, f"Cache grew for repeated keys: size={stats['size']}"
