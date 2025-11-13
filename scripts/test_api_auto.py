"""
Test API endpoints automatically (no user input required)

This script tests all API endpoints with real HTTP requests.
Make sure the server is running first: python scripts/start_api.py
"""

import requests
import json
import time
from typing import Dict, Any

# Fix Unicode encoding for Windows
import sys
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


BASE_URL = "http://localhost:8000"


def print_response(name: str, response: requests.Response):
    """Pretty print HTTP response"""
    print(f"\n{'=' * 60}")
    print(f"{name}")
    print(f"{'=' * 60}")
    print(f"Status: {response.status_code}")
    print(f"Time: {response.elapsed.total_seconds():.2f}s")

    try:
        data = response.json()
        print(f"Response:\n{json.dumps(data, indent=2)}")
    except:
        print(f"Response:\n{response.text}")


def test_root():
    """Test GET /"""
    print("\n🔍 Test 1: Root Endpoint")
    response = requests.get(f"{BASE_URL}/")
    print_response("GET /", response)
    return response.status_code == 200


def test_health():
    """Test GET /health"""
    print("\n🔍 Test 2: Health Check")
    response = requests.get(f"{BASE_URL}/health")
    print_response("GET /health", response)

    if response.status_code == 200:
        data = response.json()
        print(f"\n📊 Health Status:")
        print(f"   Status: {data.get('status')}")
        print(f"   Database: {data.get('database')}")
        print(f"   LLM: {data.get('llm')}")
        print(f"   Version: {data.get('version')}")

    return response.status_code == 200


def test_stats():
    """Test GET /api/v1/stats"""
    print("\n🔍 Test 3: Database Statistics")
    response = requests.get(f"{BASE_URL}/api/v1/stats")
    print_response("GET /api/v1/stats", response)

    if response.status_code == 200:
        data = response.json()
        print(f"\n📊 Database Stats:")
        print(f"   Managers: {data.get('managers_count'):,}")
        print(f"   Issuers: {data.get('issuers_count'):,}")
        print(f"   Filings: {data.get('filings_count'):,}")
        print(f"   Holdings: {data.get('holdings_count'):,}")
        print(f"   Latest Quarter: {data.get('latest_quarter')}")
        if data.get('total_value'):
            print(f"   Total Value: ${data.get('total_value'):,}")

    return response.status_code == 200


def test_query_simple():
    """Test POST /api/v1/query with simple question"""
    print("\n🔍 Test 4: Simple Query (No SQL)")

    payload = {
        "query": "How many managers are in the database?",
        "include_sql": False,
        "include_raw_data": False
    }

    response = requests.post(
        f"{BASE_URL}/api/v1/query",
        json=payload,
        headers={"Content-Type": "application/json"}
    )

    print_response("POST /api/v1/query (simple)", response)

    if response.status_code == 200:
        data = response.json()
        print(f"\n💬 Answer: {data.get('answer')}")
        print(f"⏱️  Execution: {data.get('execution_time_ms')}ms")
        print(f"🔧 Tool calls: {data.get('tool_calls')}")
        print(f"🔄 Turns: {data.get('turns')}")

    return response.status_code == 200


def test_query_with_sql():
    """Test POST /api/v1/query with SQL included"""
    print("\n🔍 Test 5: Query with SQL")

    payload = {
        "query": "What are the top 3 managers by portfolio value?",
        "include_sql": True,
        "include_raw_data": False
    }

    response = requests.post(
        f"{BASE_URL}/api/v1/query",
        json=payload,
        headers={"Content-Type": "application/json"}
    )

    print_response("POST /api/v1/query (with SQL)", response)

    if response.status_code == 200:
        data = response.json()
        print(f"\n💬 Answer: {data.get('answer')}")

        if data.get('sql_query'):
            print(f"\n📝 Generated SQL:")
            print(data.get('sql_query'))

        print(f"\n⏱️  Execution: {data.get('execution_time_ms')}ms")

    return response.status_code == 200


def test_query_with_data():
    """Test POST /api/v1/query with raw data"""
    print("\n🔍 Test 6: Query with Raw Data")

    payload = {
        "query": "Show me 2 managers from the database",
        "include_sql": True,
        "include_raw_data": True
    }

    response = requests.post(
        f"{BASE_URL}/api/v1/query",
        json=payload,
        headers={"Content-Type": "application/json"}
    )

    print_response("POST /api/v1/query (with data)", response)

    if response.status_code == 200:
        data = response.json()
        print(f"\n💬 Answer: {data.get('answer')}")

        if data.get('raw_data'):
            print(f"\n📊 Raw Data ({len(data['raw_data'])} rows):")
            for row in data['raw_data'][:3]:  # Show first 3
                print(f"   {row}")

    return response.status_code == 200


def test_invalid_query():
    """Test POST /api/v1/query with invalid input"""
    print("\n🔍 Test 7: Invalid Query (Validation)")

    payload = {
        "query": "ab",  # Too short (min 3 chars)
        "include_sql": False
    }

    response = requests.post(
        f"{BASE_URL}/api/v1/query",
        json=payload,
        headers={"Content-Type": "application/json"}
    )

    print_response("POST /api/v1/query (invalid)", response)

    # Should return 422 Unprocessable Entity
    return response.status_code == 422


def test_openapi_docs():
    """Test GET /openapi.json"""
    print("\n🔍 Test 8: OpenAPI Schema")

    response = requests.get(f"{BASE_URL}/openapi.json")

    # Don't print full response (too long)
    print(f"\n{'=' * 60}")
    print("GET /openapi.json")
    print(f"{'=' * 60}")
    print(f"Status: {response.status_code}")
    print(f"Time: {response.elapsed.total_seconds():.2f}s")

    if response.status_code == 200:
        data = response.json()
        print(f"\n📚 API Info:")
        print(f"   Title: {data.get('info', {}).get('title')}")
        print(f"   Version: {data.get('info', {}).get('version')}")
        print(f"   Endpoints: {len(data.get('paths', {}))}")

    return response.status_code == 200


def main():
    print("=" * 60)
    print("FastAPI Automated Testing")
    print("=" * 60)
    print(f"\nBase URL: {BASE_URL}")

    # Check if server is running
    print("\n🔌 Checking server connectivity...")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        print("✅ Server is running!")
    except requests.exceptions.ConnectionError:
        print("❌ Server not running!")
        print("\nStart the server first:")
        print("   .venv/Scripts/python.exe scripts/start_api.py")
        return 1
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1

    # Run tests
    results = []

    print("\n" + "=" * 60)
    print("Basic Endpoint Tests")
    print("=" * 60)

    results.append(("Root endpoint", test_root()))
    results.append(("Health check", test_health()))
    results.append(("Database stats", test_stats()))
    results.append(("OpenAPI docs", test_openapi_docs()))

    # Query tests (require API key)
    print("\n" + "=" * 60)
    print("Natural Language Query Tests")
    print("=" * 60)
    print("\n⚠️  Testing with ANTHROPIC_API_KEY from .env")
    print("   (Database is empty - queries will return 'no data' responses)")

    results.append(("Simple query", test_query_simple()))
    time.sleep(2)  # Rate limiting
    results.append(("Query with SQL", test_query_with_sql()))
    time.sleep(2)
    results.append(("Query with data", test_query_with_data()))
    results.append(("Invalid query validation", test_invalid_query()))

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")

    print(f"\n{passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed!")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")

    print("\n" + "=" * 60)
    print("Next Steps:")
    print("=" * 60)
    print("1. View interactive docs: http://localhost:8000/docs")
    print("2. Try queries in Swagger UI")
    print("3. Load Form 13F data to get real results")
    print("4. Deploy to Railway when ready")

    return 0 if passed == total else 1


if __name__ == "__main__":
    exit(main())
