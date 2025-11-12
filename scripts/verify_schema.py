"""Verify database schema is set up correctly."""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text, inspect
from dotenv import load_dotenv
import os

# Fix Unicode encoding for Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def main():
    load_dotenv()
    database_url = os.getenv("DATABASE_URL")

    engine = create_engine(database_url)
    inspector = inspect(engine)

    print("=" * 60)
    print("Database Schema Verification")
    print("=" * 60)

    # Check tables
    print("\n✅ Tables:")
    for table in inspector.get_table_names():
        columns = inspector.get_columns(table)
        indexes = inspector.get_indexes(table)
        print(f"\n   {table}:")
        print(f"      Columns: {len(columns)}")
        print(f"      Indexes: {len(indexes)}")

        # Show column details
        for col in columns[:3]:  # First 3 columns
            print(f"         - {col['name']}: {col['type']}")
        if len(columns) > 3:
            print(f"         ... and {len(columns) - 3} more")

    # Check row counts
    print("\n✅ Row Counts:")
    with engine.connect() as conn:
        for table in ['managers', 'issuers', 'filings', 'holdings']:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
            count = result.scalar()
            print(f"   {table}: {count:,} rows")

    print("\n" + "=" * 60)
    print("Verification complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
