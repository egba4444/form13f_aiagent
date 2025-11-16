"""
Analytics and Monitoring

Tracks API usage, query performance, and errors.
"""

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List
import threading

# In-memory analytics store (for simplicity - could use Redis/database in production)
class Analytics:
    def __init__(self):
        self.lock = threading.Lock()
        self.query_count = 0
        self.error_count = 0
        self.total_response_time_ms = 0
        self.queries_by_hour: Dict[str, int] = defaultdict(int)
        self.errors_by_type: Dict[str, int] = defaultdict(int)
        self.slow_queries: List[Dict] = []  # Queries taking > 10 seconds
        self.recent_queries: List[Dict] = []  # Last 100 queries

    def record_query(self, query: str, response_time_ms: int, success: bool, error: str = None):
        """Record a query execution"""
        with self.lock:
            self.query_count += 1
            self.total_response_time_ms += response_time_ms

            # Track by hour
            hour_key = datetime.now().strftime("%Y-%m-%d %H:00")
            self.queries_by_hour[hour_key] += 1

            # Track errors
            if not success:
                self.error_count += 1
                if error:
                    error_type = error.split(":")[0] if ":" in error else "Unknown"
                    self.errors_by_type[error_type] += 1

            # Track slow queries (> 10 seconds)
            if response_time_ms > 10000:
                self.slow_queries.append({
                    "query": query[:100],  # Truncate long queries
                    "response_time_ms": response_time_ms,
                    "timestamp": datetime.now().isoformat(),
                    "success": success
                })
                # Keep only last 50 slow queries
                self.slow_queries = self.slow_queries[-50:]

            # Track recent queries
            self.recent_queries.append({
                "query": query[:100],
                "response_time_ms": response_time_ms,
                "timestamp": datetime.now().isoformat(),
                "success": success,
                "error": error
            })
            # Keep only last 100 queries
            self.recent_queries = self.recent_queries[-100:]

    def get_stats(self) -> Dict:
        """Get analytics summary"""
        with self.lock:
            avg_response_time = (
                self.total_response_time_ms / self.query_count
                if self.query_count > 0 else 0
            )

            # Get queries from last 24 hours
            now = datetime.now()
            last_24h_queries = sum(
                count for hour_key, count in self.queries_by_hour.items()
                if (now - datetime.strptime(hour_key, "%Y-%m-%d %H:00")) <= timedelta(hours=24)
            )

            return {
                "total_queries": self.query_count,
                "total_errors": self.error_count,
                "success_rate": (
                    ((self.query_count - self.error_count) / self.query_count * 100)
                    if self.query_count > 0 else 100.0
                ),
                "average_response_time_ms": round(avg_response_time, 2),
                "queries_last_24h": last_24h_queries,
                "slow_queries_count": len([q for q in self.slow_queries if q["success"]]),
                "errors_by_type": dict(self.errors_by_type),
                "recent_queries": self.recent_queries[-10:],  # Last 10 queries
                "slow_queries": self.slow_queries[-10:]  # Last 10 slow queries
            }

    def reset(self):
        """Reset all analytics"""
        with self.lock:
            self.query_count = 0
            self.error_count = 0
            self.total_response_time_ms = 0
            self.queries_by_hour.clear()
            self.errors_by_type.clear()
            self.slow_queries.clear()
            self.recent_queries.clear()


# Global analytics instance
analytics = Analytics()
