"""
Test Vector Store 10-K Integration

Tests the new 10-K metadata support in vector store:
- Clear collection
- Upload chunks with 10-K metadata
- Search with 10-K filters
"""

from dotenv import load_dotenv
load_dotenv()

from src.rag.vector_store import get_vector_store
from src.rag.chunker import TextChunk
from src.rag.embedding_service import get_embedding_service


def test_vector_store_10k():
    print("=== Testing Vector Store 10-K Integration ===\n")

    # Get vector store
    print("1. Connecting to Qdrant...")
    vector_store = get_vector_store()

    # Get current collection info
    info = vector_store.get_collection_info()
    if info:
        print(f"   Current collection has {info['points_count']} points")

    # Clear collection
    print("\n2. Clearing collection (removing old 13F data)...")
    vector_store.clear_collection()
    print("   Collection cleared and recreated with 10-K indexes")

    # Create test chunks with 10-K data
    print("\n3. Creating test chunks...")
    test_chunks = [
        TextChunk(
            text="Apple Inc. designs, manufactures and markets smartphones, personal computers, tablets, wearables and accessories.",
            accession_number="0000320193-23-000106",
            content_type="10-K",
            chunk_index=0,
            total_chunks=3,
            char_start=0,
            char_end=110
        ),
        TextChunk(
            text="The Company's business, reputation, results of operations can be affected by macroeconomic conditions including recession, inflation, and currency fluctuations.",
            accession_number="0000320193-23-000106",
            content_type="10-K",
            chunk_index=1,
            total_chunks=3,
            char_start=110,
            char_end=270
        ),
        TextChunk(
            text="The Company has international operations with sales outside the U.S. representing a majority of total net sales.",
            accession_number="0000320193-23-000106",
            content_type="10-K",
            chunk_index=2,
            total_chunks=3,
            char_start=270,
            char_end=383
        ),
    ]
    print(f"   Created {len(test_chunks)} test chunks")

    # Generate embeddings
    print("\n4. Generating embeddings...")
    embedding_service = get_embedding_service()
    texts = [chunk.text for chunk in test_chunks]
    embeddings = embedding_service.embed_batch(texts)
    print(f"   Generated {len(embeddings)} embeddings")

    # Upload with 10-K metadata
    print("\n5. Uploading chunks with 10-K metadata...")
    uploaded = vector_store.upload_chunks(
        chunks=test_chunks,
        embeddings=embeddings,
        cik_company="0000320193",
        filing_year=2023,
        section_name="Item 1A"
    )
    print(f"   Uploaded {uploaded} chunks")

    # Test search without filters
    print("\n6. Testing search without filters...")
    query_text = "What are the main business activities?"
    query_embedding = embedding_service.embed_text(query_text)
    results = vector_store.search(
        query_embedding=query_embedding,
        top_k=2
    )
    print(f"   Found {len(results)} results:")
    for i, result in enumerate(results):
        print(f"   {i+1}. Score: {result['score']:.3f}")
        print(f"      Text: {result['text'][:80]}...")
        print(f"      CIK: {result.get('cik_company', 'N/A')}")
        print(f"      Section: {result.get('section_name', 'N/A')}")
        print(f"      Year: {result.get('filing_year', 'N/A')}")

    # Test search with company filter
    print("\n7. Testing search with CIK filter...")
    results = vector_store.search(
        query_embedding=query_embedding,
        top_k=2,
        filter_cik_company="0000320193"
    )
    print(f"   Found {len(results)} results for CIK 0000320193")

    # Test search with section filter
    print("\n8. Testing search with section filter...")
    results = vector_store.search(
        query_embedding=query_embedding,
        top_k=2,
        filter_section="Item 1A"
    )
    print(f"   Found {len(results)} results for Item 1A")

    # Test search with year filter
    print("\n9. Testing search with year filter...")
    results = vector_store.search(
        query_embedding=query_embedding,
        top_k=2,
        filter_year=2023
    )
    print(f"   Found {len(results)} results for year 2023")

    # Get final collection info
    print("\n10. Final collection info:")
    info = vector_store.get_collection_info()
    if info:
        print(f"    Total points: {info['points_count']}")
        print(f"    Status: {info['status']}")

    print("\n[SUCCESS] All vector store 10-K tests completed successfully!")


if __name__ == "__main__":
    test_vector_store_10k()
