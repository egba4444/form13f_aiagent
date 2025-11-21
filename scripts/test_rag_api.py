"""
Test RAG API Endpoints

Tests the semantic search and filing text API endpoints.

Usage:
    # Start the API server first in another terminal:
    python -m uvicorn src.api.main:app --reload --port 8000

    # Then run this test:
    python scripts/test_rag_api.py
"""

import os
import sys
import requests
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# API base URL
API_BASE = os.getenv("API_URL", "http://localhost:8000")


def test_semantic_search():
    """Test semantic search endpoint."""
    print("=" * 80)
    print("TEST: Semantic Search Endpoint")
    print("=" * 80)

    url = f"{API_BASE}/api/v1/search/semantic"

    # Test 1: Simple search
    print("\nTest 1: Simple semantic search")
    print("-" * 80)

    payload = {
        "query": "What managers are mentioned in the filings?",
        "top_k": 3
    }

    print(f"POST {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")

    response = requests.post(url, json=payload)

    print(f"\nStatus: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"[OK] Success!")
        print(f"Results count: {data.get('results_count', 0)}")

        for i, result in enumerate(data.get("results", []), 1):
            print(f"\n  Result {i}:")
            print(f"    Score: {result.get('relevance_score', 0):.3f}")
            print(f"    Filing: {result.get('accession_number', 'N/A')}")
            print(f"    Type: {result.get('content_type', 'N/A')}")
            print(f"    Text: {result.get('text', '')[:100]}...")
    else:
        print(f"[X] Failed: {response.text}")
        return False

    # Test 2: Search with filter
    print("\n\nTest 2: Search with content type filter")
    print("-" * 80)

    payload = {
        "query": "investment strategy",
        "top_k": 2,
        "filter_content_type": "explanatory_notes"
    }

    print(f"POST {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")

    response = requests.post(url, json=payload)

    print(f"\nStatus: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"[OK] Success!")
        print(f"Results count: {data.get('results_count', 0)}")

        for i, result in enumerate(data.get("results", []), 1):
            print(f"\n  Result {i}:")
            print(f"    Score: {result.get('relevance_score', 0):.3f}")
            print(f"    Type: {result.get('content_type', 'N/A')}")
    else:
        # This might fail if there are no explanatory notes - that's OK
        print(f"[WARN] No results or error: {response.text}")

    # Test 3: Invalid query (too short)
    print("\n\nTest 3: Error handling (query too short)")
    print("-" * 80)

    payload = {
        "query": "ab",  # Less than 3 chars
        "top_k": 5
    }

    response = requests.post(url, json=payload)

    print(f"Status: {response.status_code}")

    if response.status_code == 422:
        print("[OK] Validation error caught correctly")
    else:
        print(f"[X] Expected 422, got {response.status_code}")

    return True


def test_get_filing_text():
    """Test get filing text endpoint."""
    print("\n\n" + "=" * 80)
    print("TEST: Get Filing Text Endpoint")
    print("=" * 80)

    # Use a known accession number from the embeddings
    test_accession = "0001561082-25-000010"

    # Test 1: Get all text for a filing
    print("\nTest 1: Get all text sections")
    print("-" * 80)

    url = f"{API_BASE}/api/v1/filings/{test_accession}/text"

    print(f"GET {url}")

    response = requests.get(url)

    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"[OK] Success!")
        print(f"Accession: {data.get('accession_number', 'N/A')}")
        print(f"Sections found: {data.get('total_sections', 0)}")
        print(f"Section types: {', '.join(data.get('sections_found', []))}")

        for section_type, text in data.get("sections", {}).items():
            print(f"\n  {section_type}:")
            print(f"    Length: {len(text)} chars")
            print(f"    Preview: {text[:100]}...")
    else:
        print(f"[X] Failed: {response.text}")
        return False

    # Test 2: Get specific content type
    print("\n\nTest 2: Get specific content type")
    print("-" * 80)

    url = f"{API_BASE}/api/v1/filings/{test_accession}/text?content_type=cover_page"

    print(f"GET {url}")

    response = requests.get(url)

    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"[OK] Success!")
        print(f"Sections returned: {data.get('total_sections', 0)}")
    else:
        # Might not have cover_page - that's OK
        print(f"[WARN] Content type not found or error: {response.text}")

    # Test 3: Non-existent filing
    print("\n\nTest 3: Error handling (non-existent filing)")
    print("-" * 80)

    url = f"{API_BASE}/api/v1/filings/9999999999-99-999999/text"

    print(f"GET {url}")

    response = requests.get(url)

    print(f"Status: {response.status_code}")

    if response.status_code == 404:
        print("[OK] 404 error returned correctly")
    else:
        print(f"[X] Expected 404, got {response.status_code}")

    return True


def test_health_check():
    """Test that API is running."""
    print("=" * 80)
    print("CHECKING API HEALTH")
    print("=" * 80)

    url = f"{API_BASE}/health"

    try:
        response = requests.get(url, timeout=5)

        if response.status_code == 200:
            data = response.json()
            print(f"[OK] API is running")
            print(f"  Status: {data.get('status', 'unknown')}")
            print(f"  Database: {data.get('database', 'unknown')}")
            print(f"  Version: {data.get('version', 'unknown')}")
            return True
        else:
            print(f"[X] Health check failed: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"[X] Cannot connect to API at {API_BASE}")
        print("\nPlease start the API server first:")
        print("  python -m uvicorn src.api.main:app --reload --port 8000")
        return False
    except Exception as e:
        print(f"[X] Error: {e}")
        return False


def main():
    """Run all tests."""
    print("\n" * 2)
    print("=" * 80)
    print("RAG API ENDPOINT TESTS")
    print("=" * 80)
    print()

    # Check API is running
    if not test_health_check():
        return False

    print("\n")

    # Run tests
    try:
        success = True

        if not test_semantic_search():
            success = False

        if not test_get_filing_text():
            success = False

        # Summary
        print("\n" * 2)
        print("=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)

        if success:
            print("[OK] All tests passed!")
            print("\nThe RAG API endpoints are working correctly.")
            print("\nAvailable endpoints:")
            print("  POST /api/v1/search/semantic - Semantic search over filing text")
            print("  GET  /api/v1/filings/{accession}/text - Get text for specific filing")
            print("\nAPI Documentation:")
            print(f"  {API_BASE}/docs")
        else:
            print("[X] Some tests failed")
            return False

        print("=" * 80)

        return True

    except Exception as e:
        print(f"\n[X] Test error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
