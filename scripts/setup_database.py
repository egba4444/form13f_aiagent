"""
Setup database schema for Form 13F AI Agent.

This script creates the database schema by executing SQL files in the schema/ directory.
Works with both Docker PostgreSQL and Supabase.

Usage:
    python scripts/setup_database.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

# Fix Unicode encoding for Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def main():
    """Setup database schema"""
    print("=" * 60)
    print("Form 13F Database Schema Setup")
    print("=" * 60)

    # Load environment variables
    load_dotenv()

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ ERROR: DATABASE_URL not found in .env file")
        print("\nPlease set DATABASE_URL in your .env file:")
        print("  For Docker: postgresql://form13f_user:changeme123@localhost:5432/form13f")
        print("  For Supabase: postgresql://postgres.xxxxx:[PASSWORD]@...supabase.com:5432/postgres")
        return 1

    print(f"\n📦 Connecting to database...")
    print(f"   URL: {database_url.split('@')[1] if '@' in database_url else 'localhost'}")

    try:
        # Create engine
        engine = create_engine(database_url)

        # Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version();"))
            version = result.scalar()
            print(f"✅ Connected successfully!")
            print(f"   PostgreSQL version: {version.split(',')[0]}\n")

        # Read schema file
        schema_file = project_root / "schema" / "001_initial_schema.sql"

        if not schema_file.exists():
            print(f"❌ ERROR: Schema file not found: {schema_file}")
            return 1

        print(f"📄 Reading schema file: {schema_file.name}")
        schema_sql = schema_file.read_text()

        # Execute schema
        print(f"🔨 Creating tables and indexes...")

        with engine.connect() as conn:
            # Execute the entire schema file
            conn.execute(text(schema_sql))
            conn.commit()

        print("✅ Schema created successfully!\n")

        # Verify tables
        print("📊 Verifying tables...")
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """))

            tables = [row[0] for row in result]

            if tables:
                print(f"   Found {len(tables)} tables:")
                for table in tables:
                    print(f"     - {table}")
            else:
                print("   ⚠️  No tables found!")

        print("\n" + "=" * 60)
        print("✅ Database setup complete!")
        print("=" * 60)
        print("\nNext steps:")
        print("  1. Load data: python -m src.ingestion.ingest")
        print("  2. Verify data: psql and run SELECT COUNT(*) FROM holdings;")
        print("")

        return 0

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        print("\nTroubleshooting:")
        print("  1. Check DATABASE_URL in .env is correct")
        print("  2. For Docker: Ensure 'docker compose up -d postgres' is running")
        print("  3. For Supabase: Check your connection string from dashboard")
        return 1


if __name__ == "__main__":
    exit(main())
