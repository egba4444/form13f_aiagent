"""
Test RAG Setup

Verifies that all RAG components are working:
1. Qdrant connection
2. Embedding model loading
3. Text chunking
4. Embedding generation
5. Vector storage and retrieval

Usage:
    python scripts/test_rag_setup.py
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
from src.rag.chunker import TextChunker, TextChunk

# Load environment
load_dotenv()

def main():
    print("=" * 80)
    print("RAG SYSTEM SETUP TEST")
    print("=" * 80)

    # Test 1: Configuration
    print("\nTest 1: Loading configuration...")
    try:
        config = get_rag_config()
        print(f"  Qdrant URL: {config.qdrant_url}")
        print(f"  Collection: {config.qdrant_collection_name}")
        print(f"  Embedding model: {config.embedding_model}")
        print(f"  Embedding dimension: {config.embedding_dimension}")
        print(f"  Chunk size: {config.chunk_size}")
        print("  [OK] Configuration loaded")
    except Exception as e:
        print(f"  [X] Configuration failed: {e}")
        return False

    # Test 2: Qdrant connection
    print("\nTest 2: Connecting to Qdrant...")
    try:
        vector_store = get_vector_store(config)
        collections = vector_store.client.get_collections()
        print(f"  Connected to Qdrant")
        print(f"  Existing collections: {[c.name for c in collections.collections]}")
        print("  [OK] Qdrant connection successful")
    except Exception as e:
        print(f"  [X] Qdrant connection failed: {e}")
        print(f"  Make sure Qdrant is running: docker-compose up -d qdrant")
        return False

    # Test 3: Embedding model
    print("\nTest 3: Loading embedding model...")
    try:
        embedding_service = get_embedding_service(config)
        print(f"  Model: {embedding_service.model_name}")
        print(f"  Dimension: {embedding_service.dimension}")
        print("  [OK] Embedding model loaded")
    except Exception as e:
        print(f"  [X] Embedding model failed: {e}")
        return False

    # Test 4: Text chunking
    print("\nTest 4: Testing text chunking...")
    try:
        chunker = TextChunker(config)

        test_text = """
        This is a test document about Form 13F institutional holdings.
        The Form 13F is a quarterly report filed by institutional investment managers.
        These filings provide transparency into the holdings of large institutions.
        Investors and analysts use this data to track institutional investment trends.
        The data includes information about securities, share counts, and market values.
        """

        chunks = chunker.chunk_text(
            text=test_text,
            accession_number="TEST-001",
            content_type="test"
        )

        print(f"  Created {len(chunks)} chunks")
        if chunks:
            print(f"  First chunk: {chunks[0].text[:60]}...")
        print("  [OK] Text chunking working")
    except Exception as e:
        print(f"  [X] Text chunking failed: {e}")
        return False

    # Test 5: Embedding generation
    print("\nTest 5: Testing embedding generation...")
    try:
        test_texts = [
            "Form 13F institutional holdings data",
            "Quarterly portfolio disclosures",
            "Warren Buffett's Berkshire Hathaway holdings"
        ]

        embeddings = embedding_service.embed_batch(test_texts, show_progress=False)

        print(f"  Generated {len(embeddings)} embeddings")
        print(f"  Embedding dimension: {len(embeddings[0])}")

        # Test similarity
        sim = embedding_service.similarity(embeddings[0], embeddings[1])
        print(f"  Similarity (text 1 vs 2): {sim:.3f}")

        print("  [OK] Embedding generation working")
    except Exception as e:
        print(f"  [X] Embedding generation failed: {e}")
        return False

    # Test 6: Vector storage
    print("\nTest 6: Testing vector storage...")
    try:
        # Create test collection
        test_collection = "test_rag_collection"
        original_collection = vector_store.collection_name
        vector_store.collection_name = test_collection

        # Create collection
        vector_store.create_collection(recreate=True)
        print(f"  Created test collection: {test_collection}")

        # Upload test data
        test_chunks = [
            TextChunk(
                text=text,
                accession_number=f"TEST-{i:03d}",
                content_type="test",
                chunk_index=0,
                total_chunks=1,
                char_start=0,
                char_end=len(text)
            )
            for i, text in enumerate(test_texts)
        ]

        uploaded = vector_store.upload_chunks(test_chunks, embeddings)
        print(f"  Uploaded {uploaded} points")

        # Test search
        query = "institutional portfolio holdings"
        query_embedding = embedding_service.get_query_embedding(query)

        results = vector_store.search(
            query_embedding=query_embedding,
            top_k=2
        )

        print(f"  Search query: '{query}'")
        print(f"  Found {len(results)} results")
        if results:
            print(f"  Top result: '{results[0]['text'][:50]}...' (score: {results[0]['score']:.3f})")

        # Clean up
        vector_store.delete_collection()
        print(f"  Deleted test collection")

        # Restore original collection name
        vector_store.collection_name = original_collection

        print("  [OK] Vector storage working")
    except Exception as e:
        print(f"  [X] Vector storage failed: {e}")
        # Try to clean up
        try:
            vector_store.delete_collection()
        except:
            pass
        return False

    # All tests passed
    print("\n" + "=" * 80)
    print("[OK] ALL TESTS PASSED - RAG SYSTEM IS READY")
    print("=" * 80)
    print("\nNext steps:")
    print("1. Generate embeddings: python scripts/generate_embeddings.py")
    print("2. Test search: python scripts/test_rag_search.py")
    print("3. Integrate with agent")
    print("=" * 80)

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
