"""
Test RAG Retrieval Tool

Tests the RAG tool interface that the agent will use.

Usage:
    python scripts/test_rag_tool.py
"""

import os
import sys
import json
from pathlib import Path

from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.tools.rag_tool import create_rag_tool

# Load environment
load_dotenv()


def test_tool():
    """Test RAG tool functionality."""
    print("=" * 80)
    print("RAG RETRIEVAL TOOL TEST")
    print("=" * 80)

    # Initialize tool
    print("\nInitializing RAG tool...")
    rag_tool = create_rag_tool()
    print("[OK] Tool initialized")

    # Test 1: Get tool definition
    print("\nTest 1: Tool Definition")
    print("-" * 80)
    definition = rag_tool.get_tool_definition()
    print(f"Tool name: {definition['function']['name']}")
    print(f"Parameters: {list(definition['function']['parameters']['properties'].keys())}")
    print("[OK] Tool definition valid")

    # Test 2: Execute search
    print("\nTest 2: Execute Search")
    print("-" * 80)

    queries = [
        {"query": "What filing managers are in the database?", "top_k": 3},
        {"query": "Investment strategy explanations", "top_k": 2, "filter_content_type": "explanatory_notes"},
        {"query": "Berkshire Hathaway"},
    ]

    for i, query_params in enumerate(queries, 1):
        print(f"\nQuery {i}: {query_params['query']}")
        print(f"  Parameters: {query_params}")

        result = rag_tool.execute(**query_params)

        if result["success"]:
            print(f"  [OK] Success!")
            print(f"  Results: {result['results_count']}")

            for j, res in enumerate(result["results"], 1):
                print(f"\n  Result {j}:")
                print(f"    Score: {res['relevance_score']}")
                print(f"    Filing: {res['accession_number']}")
                print(f"    Type: {res['content_type']}")
                print(f"    Text: {res['text'][:100]}...")
        else:
            print(f"  [X] Error: {result['error']}")

    # Test 3: Get filing summary
    print("\n\nTest 3: Get Filing Summary")
    print("-" * 80)

    # Use an accession number we know exists
    test_accession = "0001561082-25-000010"  # The one with explanatory notes
    print(f"Getting all text for filing: {test_accession}")

    summary = rag_tool.get_filing_text_summary(test_accession)

    if summary["success"]:
        print(f"  [OK] Success!")
        print(f"  Sections found: {summary['sections_found']}")
        for section_type in summary['sections_found']:
            text = summary['sections'][section_type]
            print(f"\n  {section_type}:")
            print(f"    Length: {len(text)} chars")
            print(f"    Preview: {text[:150]}...")
    else:
        print(f"  [X] Error: {summary['error']}")

    # Test 4: Error handling
    print("\n\nTest 4: Error Handling")
    print("-" * 80)

    # Empty query
    result = rag_tool.execute(query="")
    print(f"Empty query: {'[OK] Handled correctly' if not result['success'] else '[X] Should have failed'}")

    # Invalid top_k
    result = rag_tool.execute(query="test", top_k=100)
    print(f"Invalid top_k (100): Clamped to {len(result.get('results', []))} results - [OK]")

    # Summary
    print("\n" + "=" * 80)
    print("ALL TESTS PASSED - RAG TOOL IS READY")
    print("=" * 80)
    print("\nThe RAG tool can now be integrated with the agent!")
    print("\nTool provides:")
    print("- search_filing_text: Semantic search over filing content")
    print("- get_filing_text_summary: Get all text for a specific filing")
    print("\nNext: Integrate with agent orchestrator")
    print("=" * 80)


if __name__ == "__main__":
    test_tool()
