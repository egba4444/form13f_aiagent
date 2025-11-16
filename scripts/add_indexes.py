"""
Add database indexes for performance optimization.

This script adds indexes to improve query performance, particularly for:
- Holdings sorted by value
- Holdings filtered by CUSIP
- Holdings filtered by accession_number
"""

import os
import sys
from sqlalchemy import create_engine, text

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.api.dependencies import get_database_url


def add_indexes():
    """Add indexes to database tables"""
    print("=" * 60)
    print("Adding Database Indexes")
    print("=" * 60)

    database_url = get_database_url()
    engine = create_engine(database_url)

    indexes = [
        # Holdings indexes
        ("idx_holdings_value", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_holdings_value ON holdings (value DESC)"),
        ("idx_holdings_cusip", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_holdings_cusip ON holdings (cusip)"),
        ("idx_holdings_accession", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_holdings_accession_number ON holdings (accession_number)"),

        # Filings indexes
        ("idx_filings_period", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_filings_period ON filings (period_of_report DESC)"),
        ("idx_filings_cik_period", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_filings_cik_period ON filings (cik, period_of_report DESC)"),

        # Issuers index
        ("idx_issuers_name", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_issuers_name ON issuers (LOWER(name))"),

        # Managers index
        ("idx_managers_name", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_managers_name ON managers (LOWER(name))"),
    ]

    with engine.connect() as conn:
        # Use autocommit mode for CREATE INDEX CONCURRENTLY
        conn.execution_options(isolation_level="AUTOCOMMIT")

        for idx_name, sql in indexes:
            try:
                print(f"\n[INFO] Creating index {idx_name}...", end=" ")
                conn.execute(text(sql))
                print("[OK]")
            except Exception as e:
                if "already exists" in str(e):
                    print("(already exists)")
                else:
                    print(f"[FAIL] Error: {e}")

    print("\n" + "=" * 60)
    print("[PASS] Database indexes added successfully!")
    print("=" * 60)

    # Show index sizes
    print("\nIndex sizes:")
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT
                schemaname,
                tablename,
                indexname,
                pg_size_pretty(pg_relation_size(indexname::regclass)) as size
            FROM pg_indexes
            WHERE schemaname = 'public'
            ORDER BY tablename, indexname
        """))

        current_table = None
        for row in result:
            if row.tablename != current_table:
                print(f"\n{row.tablename}:")
                current_table = row.tablename
            print(f"  {row.indexname}: {row.size}")


if __name__ == "__main__":
    try:
        add_indexes()
    except Exception as e:
        print(f"\n[FAIL] Error adding indexes: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
