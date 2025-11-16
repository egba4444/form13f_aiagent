"""
Query Cache

Simple in-memory cache for frequent queries to reduce LLM costs.
"""

import hashlib
import threading
from datetime import datetime, timedelta
from typing import Dict, Optional


class QueryCache:
    def __init__(self, ttl_minutes: int = 60, max_size: int = 100):
        """
        Initialize query cache.

        Args:
            ttl_minutes: Time-to-live for cache entries in minutes
            max_size: Maximum number of cache entries
        """
        self.ttl = timedelta(minutes=ttl_minutes)
        self.max_size = max_size
        self.lock = threading.Lock()
        self.cache: Dict[str, Dict] = {}
        self.hits = 0
        self.misses = 0

    def _hash_query(self, query: str) -> str:
        """Generate cache key from query"""
        return hashlib.md5(query.lower().strip().encode()).hexdigest()

    def get(self, query: str) -> Optional[Dict]:
        """Get cached response for query"""
        with self.lock:
            key = self._hash_query(query)
            entry = self.cache.get(key)

            if entry:
                # Check if entry has expired
                if datetime.now() - entry["timestamp"] > self.ttl:
                    del self.cache[key]
                    self.misses += 1
                    return None

                self.hits += 1
                return entry["response"]

            self.misses += 1
            return None

    def set(self, query: str, response: Dict):
        """Cache a query response"""
        with self.lock:
            # If cache is full, remove oldest entry
            if len(self.cache) >= self.max_size:
                oldest_key = min(
                    self.cache.keys(),
                    key=lambda k: self.cache[k]["timestamp"]
                )
                del self.cache[oldest_key]

            key = self._hash_query(query)
            self.cache[key] = {
                "response": response,
                "timestamp": datetime.now()
            }

    def clear(self):
        """Clear all cache entries"""
        with self.lock:
            self.cache.clear()
            self.hits = 0
            self.misses = 0

    def get_stats(self) -> Dict:
        """Get cache statistics"""
        with self.lock:
            total = self.hits + self.misses
            hit_rate = (self.hits / total * 100) if total > 0 else 0

            return {
                "size": len(self.cache),
                "max_size": self.max_size,
                "hits": self.hits,
                "misses": self.misses,
                "hit_rate": round(hit_rate, 2),
                "ttl_minutes": int(self.ttl.total_seconds() / 60)
            }


# Global cache instance (60 minute TTL, max 100 entries)
query_cache = QueryCache(ttl_minutes=60, max_size=100)
