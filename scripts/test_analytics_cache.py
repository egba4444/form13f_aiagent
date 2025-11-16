"""
Test analytics and caching functionality.

Tests the in-memory analytics and caching without needing to run the full API.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.api.analytics import analytics
from src.api.cache import query_cache


def test_analytics():
    """Test analytics functionality"""
    print("=" * 60)
    print("Testing Analytics")
    print("=" * 60)

    # Reset analytics
    analytics.reset()

    # Record some queries
    analytics.record_query(
        query="How many managers are in the database?",
        response_time_ms=1500,
        success=True
    )

    analytics.record_query(
        query="What are the top holdings?",
        response_time_ms=2500,
        success=True
    )

    analytics.record_query(
        query="Show me broken query",
        response_time_ms=500,
        success=False,
        error="SQL Error: Invalid query"
    )

    analytics.record_query(
        query="Very slow query...",
        response_time_ms=12000,  # Slow query > 10s
        success=True
    )

    # Get stats
    stats = analytics.get_stats()

    print(f"\nTotal queries: {stats['total_queries']}")
    print(f"Total errors: {stats['total_errors']}")
    print(f"Success rate: {stats['success_rate']:.2f}%")
    print(f"Average response time: {stats['average_response_time_ms']:.2f}ms")
    print(f"Queries last 24h: {stats['queries_last_24h']}")
    print(f"Slow queries count: {stats['slow_queries_count']}")
    print(f"Errors by type: {stats['errors_by_type']}")
    print(f"Recent queries: {len(stats['recent_queries'])}")

    # Verify expected values
    assert stats['total_queries'] == 4
    assert stats['total_errors'] == 1
    assert stats['success_rate'] == 75.0
    assert stats['slow_queries_count'] == 1
    assert 'SQL Error' in stats['errors_by_type']

    print("\n[PASS] Analytics tests passed!")


def test_cache():
    """Test cache functionality"""
    print("\n" + "=" * 60)
    print("Testing Query Cache")
    print("=" * 60)

    # Clear cache
    query_cache.clear()

    # Test cache miss
    result = query_cache.get("What are the top managers?")
    assert result is None
    print("[PASS] Cache miss works")

    # Add to cache
    response_data = {
        "success": True,
        "answer": "The top managers are...",
        "execution_time_ms": 1500,
        "tool_calls": 1,
        "turns": 2
    }
    query_cache.set("What are the top managers?", response_data)
    print("[PASS] Cache set works")

    # Test cache hit
    cached = query_cache.get("What are the top managers?")
    assert cached is not None
    assert cached["answer"] == "The top managers are..."
    print("[PASS] Cache hit works")

    # Test case-insensitive and whitespace handling
    cached2 = query_cache.get("  what are the TOP managers?  ")
    assert cached2 is not None
    print("[PASS] Cache key normalization works")

    # Get stats
    stats = query_cache.get_stats()
    print(f"\nCache size: {stats['size']}/{stats['max_size']}")
    print(f"Cache hits: {stats['hits']}")
    print(f"Cache misses: {stats['misses']}")
    print(f"Hit rate: {stats['hit_rate']:.2f}%")
    print(f"TTL: {stats['ttl_minutes']} minutes")

    # Verify expected values
    assert stats['size'] == 1
    assert stats['hits'] == 2  # 2 successful gets
    assert stats['misses'] == 1  # 1 failed get
    assert stats['hit_rate'] == 66.67  # 2/3 * 100
    assert stats['ttl_minutes'] == 60

    print("\n[PASS] Cache tests passed!")


def test_cache_eviction():
    """Test cache eviction when max size reached"""
    print("\n" + "=" * 60)
    print("Testing Cache Eviction")
    print("=" * 60)

    # Clear cache
    query_cache.clear()

    # Fill cache to max (100 entries)
    print(f"Filling cache to max size ({query_cache.max_size} entries)...")
    for i in range(query_cache.max_size):
        query_cache.set(
            f"Query number {i}",
            {"answer": f"Answer {i}", "success": True}
        )

    stats = query_cache.get_stats()
    print(f"Cache size after filling: {stats['size']}")
    assert stats['size'] == query_cache.max_size
    print("[PASS] Cache filled to max")

    # Add one more - should evict oldest
    query_cache.set(
        "New query that causes eviction",
        {"answer": "New answer", "success": True}
    )

    stats = query_cache.get_stats()
    print(f"Cache size after eviction: {stats['size']}")
    assert stats['size'] == query_cache.max_size  # Should still be max
    print("[PASS] Cache eviction works (size maintained at max)")

    # Verify oldest entry was removed
    oldest = query_cache.get("Query number 0")
    assert oldest is None
    print("[PASS] Oldest entry was evicted")

    # Verify newest entry exists
    newest = query_cache.get("New query that causes eviction")
    assert newest is not None
    print("[PASS] Newest entry exists")

    print("\n[PASS] Cache eviction tests passed!")


if __name__ == "__main__":
    try:
        test_analytics()
        test_cache()
        test_cache_eviction()

        print("\n" + "=" * 60)
        print("[PASS] ALL TESTS PASSED!")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n[FAIL] Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
