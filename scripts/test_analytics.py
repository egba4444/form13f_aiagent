"""
Test Analytics API endpoints.

Simple script to verify analytics endpoints work correctly.
"""

import httpx
import json

API_BASE_URL = "http://localhost:8000"


def test_portfolio_composition():
    """Test portfolio composition endpoint"""
    print("=" * 60)
    print("Testing Portfolio Composition Endpoint")
    print("=" * 60)

    # Test Berkshire Hathaway portfolio
    cik = "0001067983"
    print(f"\n1. GET /api/v1/analytics/portfolio/{cik}...")

    response = httpx.get(f"{API_BASE_URL}/api/v1/analytics/portfolio/{cik}", timeout=30.0)
    response.raise_for_status()
    data = response.json()

    print(f"   Manager: {data['manager_name']}")
    print(f"   Period: {data['period']}")
    print(f"   Total Value: ${data['total_value']:,}")
    print(f"   Holdings: {data['number_of_holdings']}")
    print(f"\n   Top 5 Holdings:")
    for i, holding in enumerate(data['top_holdings'][:5], 1):
        print(f"   {i}. {holding['title_of_class']}: ${holding['value']:,} ({holding['percent_of_portfolio']}%)")

    print(f"\n   Concentration:")
    print(f"   - Top 5: {data['concentration']['top5_percent']}%")
    print(f"   - Top 10: {data['concentration']['top10_percent']}%")

    print("\n[PASS] Portfolio composition endpoint working!")


def test_security_analysis():
    """Test security analysis endpoint"""
    print("\n" + "=" * 60)
    print("Testing Security Analysis Endpoint")
    print("=" * 60)

    # Test Apple institutional ownership
    cusip = "037833100"  # Apple CUSIP
    print(f"\n1. GET /api/v1/analytics/security/{cusip}...")

    response = httpx.get(f"{API_BASE_URL}/api/v1/analytics/security/{cusip}", timeout=30.0)
    response.raise_for_status()
    data = response.json()

    print(f"   Security: {data['title_of_class']}")
    print(f"   Period: {data['period']}")
    print(f"   Total Institutional Shares: {data['total_institutional_shares']:,}")
    print(f"   Total Institutional Value: ${data['total_institutional_value']:,}")
    print(f"   Number of Holders: {data['number_of_holders']}")

    print(f"\n   Top 5 Institutional Holders:")
    for i, holder in enumerate(data['top_holders'][:5], 1):
        print(f"   {i}. {holder['manager_name']}: {holder['shares']:,} shares (${holder['value']:,})")

    print(f"\n   Ownership Concentration:")
    print(f"   - Top 5: {data['concentration']['top5_percent']}%")
    print(f"   - Top 10: {data['concentration']['top10_percent']}%")

    print("\n[PASS] Security analysis endpoint working!")


def test_top_movers():
    """Test top movers endpoint"""
    print("\n" + "=" * 60)
    print("Testing Top Movers Endpoint")
    print("=" * 60)

    print("\n1. GET /api/v1/analytics/movers...")

    response = httpx.get(f"{API_BASE_URL}/api/v1/analytics/movers?top_n=5", timeout=60.0)
    response.raise_for_status()
    data = response.json()

    print(f"   Period: {data['period_from']} -> {data['period_to']}")

    if data['biggest_increases']:
        print(f"\n   Biggest Increases:")
        for i, mover in enumerate(data['biggest_increases'][:3], 1):
            print(f"   {i}. {mover['manager_name']} - {mover['title_of_class']}")
            print(f"      Value: ${mover['previous_value']:,} -> ${mover['current_value']:,} ({mover['value_change_percent']:+.1f}%)")

    if data['biggest_decreases']:
        print(f"\n   Biggest Decreases:")
        for i, mover in enumerate(data['biggest_decreases'][:3], 1):
            print(f"   {i}. {mover['manager_name']} - {mover['title_of_class']}")
            print(f"      Value: ${mover['previous_value']:,} -> ${mover['current_value']:,} ({mover['value_change_percent']:+.1f}%)")

    print(f"\n   New Positions: {len(data['new_positions'])}")
    print(f"   Closed Positions: {len(data['closed_positions'])}")

    print("\n[PASS] Top movers endpoint working!")


if __name__ == "__main__":
    try:
        # Check if API is running
        print("Checking API health...")
        response = httpx.get(f"{API_BASE_URL}/health", timeout=5.0)
        response.raise_for_status()
        print("[OK] API is running\n")

        # Run tests
        test_portfolio_composition()
        test_security_analysis()
        test_top_movers()

        print("\n" + "=" * 60)
        print("[PASS] ALL ANALYTICS ENDPOINT TESTS PASSED!")
        print("=" * 60)

    except httpx.ConnectError:
        print(f"\n[FAIL] Could not connect to API at {API_BASE_URL}")
        print("Make sure the API server is running")
    except Exception as e:
        print(f"\n[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()
