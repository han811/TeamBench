"""
ProductCacheService: Caches product lookups in memory.

MEMORY LEAK: The cache dict is unbounded — every unique product_id
ever requested stays in memory forever. Under production load with
millions of unique keys, this causes OOM.

Incident pattern: Cloudflare/Netflix-style unbounded memoization caches.
"""
import time
from typing import Optional


# MEMORY LEAK: unbounded dict — no eviction policy
_cache: dict = {}
_cache_hits = 0
_cache_misses = 0


def _fetch_product_from_db(product_id: str) -> dict:
    """Simulate a DB fetch (slow)."""
    time.sleep(0.001)
    return {
        "id": product_id,
        "name": f"Product {product_id}",
        "price": len(product_id) * 1.5,
        "cached_at": time.time(),
    }


def get_product(product_id: str) -> dict:
    """Get product by ID, using in-memory cache.

    VULNERABLE: cache dict grows without bound.
    Every unique product_id is stored forever.
    Fix: implement LRU eviction with maxsize=500.
    """
    global _cache_hits, _cache_misses
    if product_id in _cache:
        _cache_hits += 1
        return _cache[product_id]
    # LEAK: no eviction before inserting
    _cache_misses += 1
    product = _fetch_product_from_db(product_id)
    _cache[product_id] = product  # grows forever
    return product


def cache_stats() -> dict:
    return {
        "size": len(_cache),
        "hits": _cache_hits,
        "misses": _cache_misses,
        "max_size": 500,
    }


def clear_cache():
    """Clear entire cache (for testing only)."""
    global _cache_hits, _cache_misses
    _cache.clear()
    _cache_hits = 0
    _cache_misses = 0
