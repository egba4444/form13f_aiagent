"""
End-to-End Integration Tests

Tests the complete system from database to API to ensure everything works together.

Usage:
    # Start API server first:
    python -m uvicorn src.api.main:app --port 8001

    # Run tests:
    python scripts/test_end_to_end.py
"""

import os
import sys
import requests
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

API_BASE = os.getenv("API_URL", "http://localhost:8001")


def test_health_check():
    """Test API health check."""
    print("\n" + "=" * 80)
    print("TEST 1: Health Check")
    print("=" * 80)

    response = requests.get(f"{API_BASE}/health", timeout=10)

    assert response.status_code == 200, f"Health check failed: {response.status_code}"

    data = response.json()
    print(f"[OK] API Status: {data.get('status')}")
    print(f"[OK] Database: {data.get('database')}")
    print(f"[OK] LLM: {data.get('llm')}")
    print(f"[OK] Version: {data.get('version')}")

    assert data.get("database") == "connected", "Database not connected"
    return True


def test_database_stats():
    """Test database statistics endpoint."""
    print("\n" + "=" * 80)
    print("TEST 2: Database Statistics")
    print("=" * 80)

    response = requests.get(f"{API_BASE}/api/v1/stats", timeout=10)

    assert response.status_code == 200, f"Stats failed: {response.status_code}"

    data = response.json()
    print(f"[OK] Managers: {data.get('managers_count')}")
    print(f"[OK] Filings: {data.get('filings_count')}")
    print(f"[OK] Holdings: {data.get('holdings_count')}")
    print(f"[OK] Latest Quarter: {data.get('latest_quarter')}")

    assert data.get("filings_count", 0) > 0, "No filings in database"
    return True


def test_semantic_search():
    """Test RAG semantic search."""
    print("\n" + "=" * 80)
    print("TEST 3: Semantic Search (RAG)")
    print("=" * 80)

    payload = {
        "query": "Evolution Wealth Management",
        "top_k": 5
    }

    response = requests.post(
        f"{API_BASE}/api/v1/search/semantic",
        json=payload,
        timeout=30
    )

    assert response.status_code == 200, f"Semantic search failed: {response.status_code}"

    data = response.json()
    print(f"[OK] Query: {data.get('query')}")
    print(f"[OK] Results: {data.get('results_count')}")

    if data.get("results_count", 0) > 0:
        result = data["results"][0]
        print(f"[OK] Top result relevance: {result.get('relevance_score'):.3f}")
        print(f"[OK] Filing: {result.get('accession_number')}")

    assert data.get("success") == True, "Search not successful"
    return True


def test_filing_text_retrieval():
    """Test filing text retrieval."""
    print("\n" + "=" * 80)
    print("TEST 4: Filing Text Retrieval")
    print("=" * 80)

    # Use a known accession number
    accession = "0001561082-25-000010"

    response = requests.get(
        f"{API_BASE}/api/v1/filings/{accession}/text",
        timeout=30
    )

    assert response.status_code == 200, f"Filing text retrieval failed: {response.status_code}"

    data = response.json()
    print(f"[OK] Filing: {data.get('accession_number')}")
    print(f"[OK] Sections: {data.get('total_sections')}")
    print(f"[OK] Section types: {', '.join(data.get('sections_found', []))}")

    assert data.get("success") == True, "Retrieval not successful"
    assert data.get("total_sections", 0) > 0, "No sections found"
    return True


def test_agent_query():
    """Test agent natural language query."""
    print("\n" + "=" * 80)
    print("TEST 5: Agent Natural Language Query")
    print("=" * 80)

    payload = {
        "query": "How many filings are in the database?",
        "include_sql": True
    }

    response = requests.post(
        f"{API_BASE}/api/v1/query",
        json=payload,
        timeout=120
    )

    assert response.status_code == 200, f"Agent query failed: {response.status_code}"

    data = response.json()
    print(f"[OK] Success: {data.get('success')}")
    print(f"[OK] Answer: {data.get('answer')[:100]}...")
    print(f"[OK] Execution time: {data.get('execution_time_ms')}ms")
    print(f"[OK] Tool calls: {data.get('tool_calls')}")

    if data.get("sql_query"):
        print(f"[OK] SQL generated: {data.get('sql_query')[:80]}...")

    assert data.get("success") == True, "Query not successful"
    return True


def test_rest_endpoints():
    """Test REST data endpoints."""
    print("\n" + "=" * 80)
    print("TEST 6: REST Data Endpoints")
    print("=" * 80)

    # Test managers endpoint
    response = requests.get(f"{API_BASE}/api/v1/managers?page_size=5", timeout=10)
    assert response.status_code == 200, f"Managers endpoint failed: {response.status_code}"

    data = response.json()
    print(f"[OK] Managers endpoint: {data.get('total')} total managers")

    # Test filings endpoint
    response = requests.get(f"{API_BASE}/api/v1/filings?page_size=5", timeout=10)
    assert response.status_code == 200, f"Filings endpoint failed: {response.status_code}"

    data = response.json()
    print(f"[OK] Filings endpoint: {data.get('total')} total filings")

    # Test holdings endpoint
    response = requests.get(f"{API_BASE}/api/v1/holdings?page_size=5", timeout=10)
    assert response.status_code == 200, f"Holdings endpoint failed: {response.status_code}"

    data = response.json()
    print(f"[OK] Holdings endpoint: {data.get('total')} total holdings")

    return True


def test_qdrant_connection():
    """Test Qdrant vector database."""
    print("\n" + "=" * 80)
    print("TEST 7: Qdrant Vector Database")
    print("=" * 80)

    try:
        from qdrant_client import QdrantClient

        client = QdrantClient("http://localhost:6333")

        # Check collections
        collections = client.get_collections()
        print(f"[OK] Qdrant connected")
        print(f"[OK] Collections: {[c.name for c in collections.collections]}")

        # Check filing_text_embeddings collection
        info = client.get_collection("filing_text_embeddings")
        print(f"[OK] Embeddings count: {info.points_count}")
        print(f"[OK] Vector size: {info.config.params.vectors.size}")

        assert info.points_count > 0, "No embeddings in collection"
        return True

    except Exception as e:
        print(f"[X] Qdrant test failed: {e}")
        return False


def test_database_connection():
    """Test direct database connection."""
    print("\n" + "=" * 80)
    print("TEST 8: Direct Database Connection")
    print("=" * 80)

    try:
        from sqlalchemy import create_engine, text
        from src.api.dependencies import get_database_url

        database_url = get_database_url()
        engine = create_engine(database_url)

        with engine.connect() as conn:
            # Test query
            result = conn.execute(text("SELECT 1")).scalar()
            print(f"[OK] Database connection successful")

            # Count tables
            count = conn.execute(text("""
                SELECT COUNT(*)
                FROM information_schema.tables
                WHERE table_schema = 'public'
            """)).scalar()
            print(f"[OK] Tables in database: {count}")

            # Check filing_text_content table
            text_count = conn.execute(text("""
                SELECT COUNT(*) FROM filing_text_content
            """)).scalar()
            print(f"[OK] Text sections in database: {text_count}")

            assert text_count > 0, "No text content in database"

        return True

    except Exception as e:
        print(f"[X] Database test failed: {e}")
        return False


def main():
    """Run all end-to-end tests."""
    print("\n" * 2)
    print("=" * 80)
    print("END-TO-END INTEGRATION TESTS")
    print("=" * 80)
    print()

    tests = [
        ("Health Check", test_health_check),
        ("Database Statistics", test_database_stats),
        ("Semantic Search (RAG)", test_semantic_search),
        ("Filing Text Retrieval", test_filing_text_retrieval),
        ("Agent Query", test_agent_query),
        ("REST Endpoints", test_rest_endpoints),
        ("Qdrant Connection", test_qdrant_connection),
        ("Database Connection", test_database_connection),
    ]

    passed = 0
    failed = 0
    errors = []

    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
                errors.append(name)
        except AssertionError as e:
            failed += 1
            errors.append(f"{name}: {str(e)}")
            print(f"[X] Test failed: {e}")
        except Exception as e:
            failed += 1
            errors.append(f"{name}: {str(e)}")
            print(f"[X] Unexpected error: {e}")

    # Summary
    print("\n" * 2)
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Total tests: {passed + failed}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")

    if failed > 0:
        print("\nFailed tests:")
        for error in errors:
            print(f"  - {error}")

    print("=" * 80)

    if failed == 0:
        print("\n[SUCCESS] All end-to-end tests passed!")
        print("\nThe system is fully operational:")
        print("  - Database connected and populated")
        print("  - Qdrant vector store operational")
        print("  - RAG system functional")
        print("  - Agent responding to queries")
        print("  - REST API endpoints working")
        print("  - Text extraction and embeddings working")
        return True
    else:
        print("\n[FAILURE] Some tests failed. Please check the errors above.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
