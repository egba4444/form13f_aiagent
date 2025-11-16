"""
Test Database Connection

Tests DATABASE_URL connection with detailed error reporting.
Run this on Railway to diagnose connection issues.
"""

import os
import sys
from sqlalchemy import create_engine, text
import traceback


def test_database_connection():
    """Test database connection with detailed diagnostics"""
    print("=" * 60)
    print("DATABASE CONNECTION TEST")
    print("=" * 60)

    # Check environment variable
    database_url = os.getenv("DATABASE_URL")
    print(f"\n1. DATABASE_URL environment variable:")
    if database_url:
        # Mask password for security
        if "@" in database_url:
            parts = database_url.split("@")
            user_part = parts[0].split("://")[0] + "://" + parts[0].split("://")[1].split(":")[0] + ":***"
            masked_url = user_part + "@" + "@".join(parts[1:])
            print(f"   ✅ Set: {masked_url}")
        else:
            print(f"   ✅ Set: {database_url}")
    else:
        print("   ❌ NOT SET")
        print("\nERROR: DATABASE_URL environment variable is not set!")
        print("Please set it in Railway dashboard → Variables tab")
        return False

    # Parse connection details
    print(f"\n2. Parsing connection details:")
    try:
        from urllib.parse import urlparse
        parsed = urlparse(database_url)
        print(f"   Scheme: {parsed.scheme}")
        print(f"   Host: {parsed.hostname}")
        print(f"   Port: {parsed.port or 5432}")
        print(f"   Database: {parsed.path.lstrip('/')}")
        print(f"   Username: {parsed.username}")
    except Exception as e:
        print(f"   ❌ Failed to parse: {e}")
        return False

    # Test connection
    print(f"\n3. Testing database connection:")
    try:
        engine = create_engine(
            database_url,
            pool_size=1,
            max_overflow=0,
            pool_pre_ping=True,
            echo=True  # Show SQL statements
        )

        print("   Attempting to connect...")
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1 as test"))
            row = result.fetchone()
            print(f"   ✅ Connection successful! Test query returned: {row[0]}")

            # Get database version
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"   PostgreSQL version: {version[:50]}...")

            # Count tables
            result = conn.execute(text("""
                SELECT COUNT(*)
                FROM information_schema.tables
                WHERE table_schema = 'public'
            """))
            table_count = result.fetchone()[0]
            print(f"   Tables in database: {table_count}")

        engine.dispose()
        return True

    except Exception as e:
        print(f"   ❌ Connection failed!")
        print(f"\nError type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        print(f"\nFull traceback:")
        traceback.print_exc()

        # Common issues
        print("\n" + "=" * 60)
        print("COMMON ISSUES:")
        print("=" * 60)
        print("1. Wrong DATABASE_URL format")
        print("   Expected: postgresql://user:password@host:port/database")
        print("")
        print("2. Supabase connection pooler mode")
        print("   Use: postgresql://postgres:password@host:6543/postgres")
        print("   NOT: postgresql://postgres:password@host:5432/postgres")
        print("")
        print("3. IP address not whitelisted in Supabase")
        print("   Check: Supabase Dashboard → Settings → Database → Connection Pooling")
        print("")
        print("4. Wrong password or credentials")
        print("   Verify: Supabase Dashboard → Settings → Database → Connection String")
        print("=" * 60)

        return False


if __name__ == "__main__":
    success = test_database_connection()
    sys.exit(0 if success else 1)
