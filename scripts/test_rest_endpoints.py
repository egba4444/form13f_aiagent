"""
Test REST API endpoints.

Simple script to verify managers, filings, and holdings endpoints work correctly.
"""

import httpx
import sys

API_BASE_URL = "http://localhost:8000"


def test_managers():
    """Test managers endpoints"""
    print("=" * 60)
    print("Testing Managers Endpoints")
    print("=" * 60)

    # Test list managers
    print("\n1. GET /api/v1/managers (first page)...")
    response = httpx.get(f"{API_BASE_URL}/api/v1/managers", params={"page": 1, "page_size": 5})
    response.raise_for_status()
    data = response.json()
    print(f"   Total managers: {data['total']}")
    print(f"   Returned {len(data['managers'])} managers")
    if data['managers']:
        print(f"   First manager: {data['managers'][0]['name']} (CIK: {data['managers'][0]['cik']})")

    # Test search by name
    print("\n2. GET /api/v1/managers?name=Berkshire...")
    response = httpx.get(f"{API_BASE_URL}/api/v1/managers", params={"name": "Berkshire"})
    response.raise_for_status()
    data = response.json()
    print(f"   Found {data['total']} managers matching 'Berkshire'")
    if data['managers']:
        print(f"   First match: {data['managers'][0]['name']}")

    # Test get specific manager
    if data['managers']:
        cik = data['managers'][0]['cik']
        print(f"\n3. GET /api/v1/managers/{cik}...")
        response = httpx.get(f"{API_BASE_URL}/api/v1/managers/{cik}")
        response.raise_for_status()
        manager = response.json()
        print(f"   Manager: {manager['name']} (CIK: {manager['cik']})")

    print("\n[PASS] Managers endpoints working!")


def test_filings():
    """Test filings endpoints"""
    print("\n" + "=" * 60)
    print("Testing Filings Endpoints")
    print("=" * 60)

    # Test list filings
    print("\n1. GET /api/v1/filings (first page)...")
    response = httpx.get(f"{API_BASE_URL}/api/v1/filings", params={"page": 1, "page_size": 5})
    response.raise_for_status()
    data = response.json()
    print(f"   Total filings: {data['total']}")
    print(f"   Returned {len(data['filings'])} filings")
    if data['filings']:
        filing = data['filings'][0]
        print(f"   Latest filing: {filing['accession_number']} (Period: {filing['period_of_report']})")
        print(f"   Holdings: {filing['number_of_holdings']}, Value: ${filing['total_value']:,}")

    # Test filter by CIK (using Berkshire's CIK)
    print("\n2. GET /api/v1/filings?cik=0001067983...")
    response = httpx.get(f"{API_BASE_URL}/api/v1/filings", params={"cik": "0001067983", "page_size": 3})
    response.raise_for_status()
    data = response.json()
    print(f"   Found {data['total']} filings from Berkshire Hathaway")
    if data['filings']:
        print(f"   Latest: Period {data['filings'][0]['period_of_report']}")

    # Test get specific filing
    if data['filings']:
        accession = data['filings'][0]['accession_number']
        print(f"\n3. GET /api/v1/filings/{accession}...")
        response = httpx.get(f"{API_BASE_URL}/api/v1/filings/{accession}")
        response.raise_for_status()
        filing = response.json()
        print(f"   Filing: {filing['accession_number']}")
        print(f"   Period: {filing['period_of_report']}, Holdings: {filing['number_of_holdings']}")

    print("\n[PASS] Filings endpoints working!")


def test_holdings():
    """Test holdings endpoints"""
    print("\n" + "=" * 60)
    print("Testing Holdings Endpoints")
    print("=" * 60)

    # Test list holdings
    print("\n1. GET /api/v1/holdings (first page)...")
    response = httpx.get(f"{API_BASE_URL}/api/v1/holdings", params={"page": 1, "page_size": 5})
    response.raise_for_status()
    data = response.json()
    print(f"   Total holdings: {data['total']}")
    print(f"   Returned {len(data['holdings'])} holdings")
    if data['holdings']:
        holding = data['holdings'][0]
        print(f"   Top holding: {holding['title_of_class']}")
        print(f"   Value: ${holding['value']:,}, Shares: {holding['shares_or_principal']:,}")

    # Test search by issuer name
    print("\n2. GET /api/v1/holdings?issuer_name=Apple...")
    response = httpx.get(f"{API_BASE_URL}/api/v1/holdings", params={"issuer_name": "Apple", "page_size": 3})
    response.raise_for_status()
    data = response.json()
    print(f"   Found {data['total']} Apple holdings")
    if data['holdings']:
        print(f"   Example: {data['holdings'][0]['title_of_class']}")
        print(f"   CUSIP: {data['holdings'][0]['cusip']}")

    # Test get specific holding
    if data['holdings']:
        holding_id = data['holdings'][0]['id']
        print(f"\n3. GET /api/v1/holdings/{holding_id}...")
        response = httpx.get(f"{API_BASE_URL}/api/v1/holdings/{holding_id}")
        response.raise_for_status()
        holding = response.json()
        print(f"   Holding: {holding['title_of_class']}")
        print(f"   CUSIP: {holding['cusip']}, Value: ${holding['value']:,}")

    print("\n[PASS] Holdings endpoints working!")


if __name__ == "__main__":
    try:
        # Check if API is running
        print("Checking API health...")
        response = httpx.get(f"{API_BASE_URL}/health", timeout=5.0)
        response.raise_for_status()
        print("[OK] API is running\n")

        # Run tests
        test_managers()
        test_filings()
        test_holdings()

        print("\n" + "=" * 60)
        print("[PASS] ALL REST ENDPOINT TESTS PASSED!")
        print("=" * 60)

    except httpx.ConnectError:
        print(f"\n[FAIL] Could not connect to API at {API_BASE_URL}")
        print("Make sure the API server is running:")
        print("  .venv/Scripts/python.exe -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000")
        sys.exit(1)
    except Exception as e:
        print(f"\n[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
