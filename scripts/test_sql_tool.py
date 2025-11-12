"""Test SQL Query Tool"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.tools import SQLQueryTool, SQLValidator, SQLValidationError
from dotenv import load_dotenv
import os

# Fix Unicode encoding for Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def main():
    load_dotenv()
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        print("❌ DATABASE_URL not set in .env")
        return 1

    print("=" * 60)
    print("SQL Query Tool Test")
    print("=" * 60)

    # Test validator first
    print("\n🔍 Testing SQL Validator...")
    validator = SQLValidator()

    # Test 1: Valid query
    try:
        safe_sql = validator.validate("SELECT * FROM managers")
        print(f"✅ Valid query: {safe_sql}")
    except SQLValidationError as e:
        print(f"❌ Unexpected error: {e}")

    # Test 2: Dangerous query
    try:
        validator.validate("DROP TABLE managers")
        print("❌ Should have caught dangerous query!")
    except SQLValidationError as e:
        print(f"✅ Caught dangerous query: {e}")

    # Test 3: Invalid table
    try:
        validator.validate("SELECT * FROM users")
        print("❌ Should have caught invalid table!")
    except SQLValidationError as e:
        print(f"✅ Caught invalid table: {e}")

    # Test SQL Tool
    print("\n📊 Testing SQL Query Tool...")
    tool = SQLQueryTool(database_url)

    # Get tool definition
    print("\n📋 Tool Definition:")
    tool_def = tool.get_tool_definition()
    print(f"   Function name: {tool_def['function']['name']}")
    print(f"   Required params: {tool_def['function']['parameters']['required']}")

    # Test query (count managers)
    print("\n🔎 Test Query 1: Count managers")
    result = tool.execute(
        "SELECT COUNT(*) as count FROM managers",
        "Count total managers in database"
    )
    print(tool.format_results(result))

    # Test query (count all tables)
    print("\n🔎 Test Query 2: Count all tables")
    result = tool.execute("""
        SELECT
            (SELECT COUNT(*) FROM managers) as managers,
            (SELECT COUNT(*) FROM issuers) as issuers,
            (SELECT COUNT(*) FROM filings) as filings,
            (SELECT COUNT(*) FROM holdings) as holdings
    """)
    print(tool.format_results(result))

    # Test invalid query
    print("\n🚫 Test Query 3: Invalid (should fail)")
    result = tool.execute("DELETE FROM managers")
    print(tool.format_results(result))

    # Show compact schema
    print("\n📄 Database Schema (compact):")
    print(tool.get_schema(compact=True))

    print("\n" + "=" * 60)
    print("✅ All tests completed!")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    exit(main())
