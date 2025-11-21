"""
Test RAG Components (Without Qdrant)

Tests the core RAG components that don't require Qdrant:
1. Configuration loading
2. Text chunking
3. Embedding generation

This is useful for testing when Qdrant isn't available.

Usage:
    python scripts/test_rag_components.py
"""

import os
import sys
from pathlib import Path
import time

from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.rag.config import get_rag_config
from src.rag.embedding_service import get_embedding_service
from src.rag.chunker import TextChunker

# Load environment
load_dotenv()


def test_configuration():
    """Test 1: Configuration loading"""
    print("\n" + "=" * 80)
    print("TEST 1: Configuration Loading")
    print("=" * 80)

    try:
        config = get_rag_config()
        print(f"[OK] Qdrant URL: {config.qdrant_url}")
        print(f"[OK] Collection: {config.qdrant_collection_name}")
        print(f"[OK] Embedding model: {config.embedding_model}")
        print(f"[OK] Embedding dimension: {config.embedding_dimension}")
        print(f"[OK] Chunk size: {config.chunk_size}")
        print(f"[OK] Chunk overlap: {config.chunk_overlap}")
        print(f"[OK] Top K: {config.top_k}")
        print(f"[OK] Score threshold: {config.score_threshold}")
        print("\n[PASS] Configuration loaded successfully")
        return True, config
    except Exception as e:
        print(f"\n[FAIL] Configuration failed: {e}")
        return False, None


def test_text_chunking(config):
    """Test 2: Text chunking"""
    print("\n" + "=" * 80)
    print("TEST 2: Text Chunking")
    print("=" * 80)

    try:
        chunker = TextChunker(config)

        # Test with realistic Form 13F text
        test_text = """
        BERKSHIRE HATHAWAY INC. is a holding company owning subsidiaries engaged in a number of
        diverse business activities. The most important of these are insurance businesses
        conducted nationwide on a primary basis and worldwide on a reinsurance basis. Our
        investment philosophy emphasizes long-term investment in businesses with strong
        competitive advantages and capable management teams. We focus on companies with
        predictable earnings, minimal debt, and strong cash generation.

        The portfolio reflects our belief in concentrated ownership of businesses we understand.
        We do not employ complex derivative strategies or engage in short-term trading. Our
        holdings are primarily in companies where we can identify sustainable competitive moats
        and where management is shareholder-oriented. This approach has served us well over
        many decades.

        Market volatility in the quarter led to some position adjustments, though our core
        holdings remain unchanged. We continue to seek businesses that can compound value over
        long periods. Our focus remains on intrinsic value rather than market sentiment.
        """

        chunks = chunker.chunk_text(
            text=test_text,
            accession_number="0001067983-25-000001",
            content_type="explanatory_notes"
        )

        print(f"[OK] Original text length: {len(test_text)} characters")
        print(f"[OK] Number of chunks created: {len(chunks)}")

        if chunks:
            print(f"\n[OK] Chunk details:")
            for i, chunk in enumerate(chunks):
                print(f"  Chunk {i+1}:")
                print(f"    - Length: {len(chunk.text)} chars")
                print(f"    - Accession: {chunk.accession_number}")
                print(f"    - Type: {chunk.content_type}")
                print(f"    - Index: {chunk.chunk_index}/{chunk.total_chunks}")
                print(f"    - Preview: {chunk.text[:80]}...")
        else:
            print("  (No chunks created - text too short)")

        print("\n[OK] PASS: Text chunking working")
        return True, chunks
    except Exception as e:
        print(f"\n[X] FAIL: Text chunking failed: {e}")
        import traceback
        traceback.print_exc()
        return False, None


def test_embedding_service(config, chunks):
    """Test 3: Embedding generation"""
    print("\n" + "=" * 80)
    print("TEST 3: Embedding Generation")
    print("=" * 80)

    try:
        print("Loading embedding model (first run may take time to download)...")
        start_time = time.time()

        embedding_service = get_embedding_service(config)
        load_time = time.time() - start_time

        print(f"[OK] Model loaded in {load_time:.2f} seconds")
        print(f"[OK] Model: {embedding_service.model_name}")
        print(f"[OK] Dimension: {embedding_service.dimension}")
        print(f"[OK] Batch size: {embedding_service.batch_size}")

        # Test single embedding
        print("\nTesting single text embedding...")
        test_text = "Form 13F institutional holdings report"

        start_time = time.time()
        embedding = embedding_service.embed_text(test_text)
        embed_time = time.time() - start_time

        print(f"[OK] Generated embedding in {embed_time*1000:.2f}ms")
        print(f"[OK] Embedding dimension: {len(embedding)}")
        print(f"[OK] Sample values: [{embedding[0]:.4f}, {embedding[1]:.4f}, {embedding[2]:.4f}, ...]")

        # Test batch embedding
        if chunks and len(chunks) > 0:
            print(f"\nTesting batch embedding ({len(chunks)} chunks)...")
            chunk_texts = [c.text for c in chunks]

            start_time = time.time()
            embeddings = embedding_service.embed_batch(chunk_texts, show_progress=True)
            batch_time = time.time() - start_time

            print(f"[OK] Generated {len(embeddings)} embeddings in {batch_time:.2f} seconds")
            print(f"[OK] Average time per embedding: {batch_time/len(embeddings)*1000:.2f}ms")

        # Test similarity
        print("\nTesting similarity calculation...")
        text1 = "Warren Buffett's investment strategy"
        text2 = "Berkshire Hathaway's portfolio approach"
        text3 = "Federal Reserve interest rate policy"

        emb1 = embedding_service.embed_text(text1)
        emb2 = embedding_service.embed_text(text2)
        emb3 = embedding_service.embed_text(text3)

        sim_12 = embedding_service.similarity(emb1, emb2)
        sim_13 = embedding_service.similarity(emb1, emb3)

        print(f"[OK] Similarity ('{text1}' vs '{text2}'): {sim_12:.3f}")
        print(f"[OK] Similarity ('{text1}' vs '{text3}'): {sim_13:.3f}")
        print(f"[OK] Related texts have higher similarity: {sim_12 > sim_13}")

        print("\n[OK] PASS: Embedding generation working")
        return True
    except Exception as e:
        print(f"\n[X] FAIL: Embedding generation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("=" * 80)
    print("RAG COMPONENTS TEST (Without Qdrant)")
    print("=" * 80)
    print("\nThis tests core RAG components that work without Qdrant.")
    print("For full RAG testing including vector search, you need to:")
    print("1. Install Docker Desktop: https://www.docker.com/products/docker-desktop/")
    print("2. Start Qdrant: docker-compose up -d qdrant")
    print("3. Run: python scripts/test_rag_setup.py")

    results = []

    # Test 1: Configuration
    success, config = test_configuration()
    results.append(("Configuration", success))

    if not success:
        print("\n[X] Cannot continue without configuration")
        return False

    # Test 2: Text Chunking
    success, chunks = test_text_chunking(config)
    results.append(("Text Chunking", success))

    # Test 3: Embedding Generation
    success = test_embedding_service(config, chunks or [])
    results.append(("Embedding Generation", success))

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    all_passed = True
    for test_name, passed in results:
        status = "[OK] PASS" if passed else "[X] FAIL"
        print(f"{status}: {test_name}")
        if not passed:
            all_passed = False

    print("=" * 80)

    if all_passed:
        print("\n[OK] All RAG components are working!")
        print("\nNext steps:")
        print("1. Install Docker Desktop (if not installed)")
        print("2. Start Qdrant: docker-compose up -d qdrant")
        print("3. Run full test: python scripts/test_rag_setup.py")
        print("4. Generate embeddings: python scripts/generate_embeddings.py")
    else:
        print("\n[X] Some tests failed. Check error messages above.")

    print("=" * 80)

    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
