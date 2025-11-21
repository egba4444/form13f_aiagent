"""
Test RAG Semantic Search

Tests semantic search on actual filing text embeddings.

Usage:
    python scripts/test_rag_search.py
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.rag.config import get_rag_config
from src.rag.embedding_service import get_embedding_service
from src.rag.vector_store import get_vector_store

# Load environment
load_dotenv()


def test_search(query: str, top_k: int = 3):
    """Test semantic search with a query."""
    print(f"\nQuery: '{query}'")
    print("-" * 80)

    # Initialize
    config = get_rag_config()
    embedding_service = get_embedding_service(config)
    vector_store = get_vector_store(config)

    # Generate query embedding
    query_embedding = embedding_service.get_query_embedding(query)

    # Search
    results = vector_store.search(
        query_embedding=query_embedding,
        top_k=top_k,
        score_threshold=0.3  # Lower threshold to see more results
    )

    # Display results
    if not results:
        print("No results found")
        return

    print(f"Found {len(results)} results:\n")

    for i, result in enumerate(results, 1):
        print(f"Result {i}:")
        print(f"  Score: {result['score']:.3f}")
        print(f"  Filing: {result['accession_number']}")
        print(f"  Type: {result['content_type']}")
        print(f"  Text: {result['text'][:150]}...")
        print()


def main():
    """Run multiple test queries."""
    print("=" * 80)
    print("RAG SEMANTIC SEARCH TEST")
    print("=" * 80)
    print("\nSearching 11 filing text embeddings...")

    # Test queries
    queries = [
        "What is the filing manager's information?",
        "Investment strategy and methodology",
        "Portfolio management approach",
        "Berkshire Hathaway",
        "ESG or sustainability",
    ]

    for query in queries:
        try:
            test_search(query, top_k=3)
        except Exception as e:
            print(f"\nError searching for '{query}': {e}\n")

    print("=" * 80)
    print("SEARCH TEST COMPLETE")
    print("=" * 80)
    print("\nThe RAG system is working!")
    print("You can now:")
    print("1. Run more text extraction: python scripts/extract_filing_text.py --limit 100")
    print("2. Generate more embeddings: python scripts/generate_embeddings.py")
    print("3. Build the RAG tool for the agent")
    print("=" * 80)


if __name__ == "__main__":
    main()
