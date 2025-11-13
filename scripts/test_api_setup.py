"""Test API Setup"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

# Fix Unicode encoding for Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def main():
    load_dotenv()

    print("=" * 60)
    print("FastAPI Setup Test")
    print("=" * 60)

    # Test 1: Import FastAPI app
    print("\n1. Testing FastAPI app import...")
    try:
        from src.api import app
        print("   ✅ FastAPI app imported successfully")
    except Exception as e:
        print(f"   ❌ Failed to import app: {e}")
        return 1

    # Test 2: Check routes
    print("\n2. Checking registered routes...")
    try:
        routes = [route.path for route in app.routes]
        print(f"   ✅ Found {len(routes)} routes:")
        for route in routes[:10]:  # Show first 10
            print(f"      - {route}")
        if len(routes) > 10:
            print(f"      ... and {len(routes) - 10} more")
    except Exception as e:
        print(f"   ❌ Failed to get routes: {e}")
        return 1

    # Test 3: Check OpenAPI schema
    print("\n3. Checking OpenAPI schema...")
    try:
        from fastapi.openapi.utils import get_openapi
        openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            routes=app.routes
        )
        endpoints = list(openapi_schema.get("paths", {}).keys())
        print(f"   ✅ OpenAPI schema generated")
        print(f"   📝 API Endpoints:")
        for endpoint in endpoints:
            print(f"      - {endpoint}")
    except Exception as e:
        print(f"   ❌ Failed to generate OpenAPI schema: {e}")
        return 1

    # Test 4: Check dependencies
    print("\n4. Checking dependencies...")
    try:
        from src.api.dependencies import get_database_url
        database_url = get_database_url()
        print(f"   ✅ DATABASE_URL configured")
    except Exception as e:
        print(f"   ⚠️  DATABASE_URL not configured: {e}")

    # Test 5: Check agent
    print("\n5. Checking agent dependency...")
    try:
        from src.api.dependencies import get_agent
        # Don't actually create the agent (might fail without API key)
        print(f"   ✅ Agent dependency available")
    except Exception as e:
        print(f"   ❌ Agent dependency error: {e}")
        return 1

    print("\n" + "=" * 60)
    print("✅ All tests passed!")
    print("=" * 60)
    print("\n📝 Next steps:")
    print("   1. Start API: python scripts/start_api.py")
    print("   2. View docs: http://localhost:8000/docs")
    print("   3. Test query: POST http://localhost:8000/api/v1/query")

    return 0


if __name__ == "__main__":
    exit(main())
