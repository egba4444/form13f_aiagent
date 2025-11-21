"""
Generate Embeddings for Filing Text

This script:
1. Fetches text content from database
2. Chunks the text into smaller pieces
3. Generates embeddings using sentence-transformers
4. Uploads embeddings to Qdrant vector database

Usage:
    # Generate embeddings for all text content
    python scripts/generate_embeddings.py

    # Recreate collection (delete existing embeddings)
    python scripts/generate_embeddings.py --recreate

    # Process only specific content types
    python scripts/generate_embeddings.py --content-type explanatory_notes

    # Process only specific accession numbers
    python scripts/generate_embeddings.py --accession 0001067983-25-000001

    # Limit number of filings to process
    python scripts/generate_embeddings.py --limit 100
"""

import os
import sys
import logging
import argparse
from pathlib import Path
from typing import List, Dict, Optional

import psycopg2
from dotenv import load_dotenv
from tqdm import tqdm

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.rag.config import get_rag_config
from src.rag.embedding_service import get_embedding_service
from src.rag.vector_store import get_vector_store
from src.rag.chunker import chunk_filing_content

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment
load_dotenv()


class EmbeddingPipeline:
    """Pipeline for generating and uploading embeddings."""

    def __init__(self, database_url: str):
        """Initialize pipeline."""
        self.database_url = database_url
        self.config = get_rag_config()

        logger.info("Initializing RAG components...")
        self.embedding_service = get_embedding_service(self.config)
        self.vector_store = get_vector_store(self.config)

        logger.info(f"Embedding model: {self.config.embedding_model}")
        logger.info(f"Embedding dimension: {self.config.embedding_dimension}")
        logger.info(f"Chunk size: {self.config.chunk_size}")
        logger.info(f"Chunk overlap: {self.config.chunk_overlap}")

    def fetch_text_content(
        self,
        content_type: Optional[str] = None,
        accession: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        Fetch text content from database.

        Args:
            content_type: Filter by content type
            accession: Filter by accession number
            limit: Limit number of rows

        Returns:
            List of dicts with text_content, accession_number, content_type
        """
        conn = psycopg2.connect(self.database_url)
        cur = conn.cursor()

        # Build query
        query = """
            SELECT accession_number, content_type, text_content
            FROM filing_text_content
            WHERE 1=1
        """
        params = []

        if content_type:
            query += " AND content_type = %s"
            params.append(content_type)

        if accession:
            query += " AND accession_number = %s"
            params.append(accession)

        query += " ORDER BY accession_number, content_type"

        if limit:
            query += f" LIMIT {limit}"

        # Execute
        cur.execute(query, params)
        rows = cur.fetchall()

        # Format results
        results = []
        for row in rows:
            results.append({
                "accession_number": row[0],
                "content_type": row[1],
                "text_content": row[2]
            })

        cur.close()
        conn.close()

        logger.info(f"Fetched {len(results)} text sections from database")
        return results

    def run(
        self,
        recreate: bool = False,
        content_type: Optional[str] = None,
        accession: Optional[str] = None,
        limit: Optional[int] = None
    ) -> Dict[str, int]:
        """
        Run the complete embedding generation pipeline.

        Args:
            recreate: Recreate collection (delete existing)
            content_type: Filter by content type
            accession: Filter by accession number
            limit: Limit number of text sections to process

        Returns:
            Dictionary with statistics
        """
        stats = {
            "text_sections": 0,
            "chunks_created": 0,
            "embeddings_generated": 0,
            "points_uploaded": 0
        }

        logger.info("=" * 80)
        logger.info("STARTING EMBEDDING GENERATION PIPELINE")
        logger.info("=" * 80)

        # Step 1: Set up Qdrant collection
        logger.info("\nStep 1: Setting up Qdrant collection...")
        self.vector_store.create_collection(recreate=recreate)

        collection_info = self.vector_store.get_collection_info()
        if collection_info:
            logger.info(f"Collection: {collection_info['name']}")
            logger.info(f"Existing points: {collection_info['points_count']}")

        # Step 2: Fetch text content
        logger.info("\nStep 2: Fetching text content from database...")
        content_rows = self.fetch_text_content(
            content_type=content_type,
            accession=accession,
            limit=limit
        )
        stats["text_sections"] = len(content_rows)

        if not content_rows:
            logger.warning("No text content found. Exiting.")
            return stats

        # Step 3: Chunk text
        logger.info("\nStep 3: Chunking text...")
        chunks = chunk_filing_content(content_rows, self.config)
        stats["chunks_created"] = len(chunks)
        logger.info(f"Created {len(chunks)} chunks from {len(content_rows)} text sections")

        if not chunks:
            logger.warning("No chunks created (all text too short). Exiting.")
            return stats

        # Show chunk statistics
        total_chars = sum(len(c.text) for c in chunks)
        avg_chars = total_chars / len(chunks)
        logger.info(f"Average chunk size: {avg_chars:.0f} characters")

        # Step 4: Generate embeddings
        logger.info("\nStep 4: Generating embeddings...")
        chunk_texts = [c.text for c in chunks]

        embeddings = self.embedding_service.embed_batch(
            chunk_texts,
            show_progress=True
        )
        stats["embeddings_generated"] = len(embeddings)
        logger.info(f"Generated {len(embeddings)} embeddings")

        # Step 5: Upload to Qdrant
        logger.info("\nStep 5: Uploading to Qdrant...")
        uploaded = self.vector_store.upload_chunks(
            chunks=chunks,
            embeddings=embeddings,
            batch_size=100
        )
        stats["points_uploaded"] = uploaded

        # Print summary
        self._print_summary(stats)

        return stats

    def _print_summary(self, stats: Dict[str, int]):
        """Print pipeline execution summary."""
        logger.info("\n" + "=" * 80)
        logger.info("EMBEDDING GENERATION SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Text sections processed:  {stats['text_sections']}")
        logger.info(f"Chunks created:           {stats['chunks_created']}")
        logger.info(f"Embeddings generated:     {stats['embeddings_generated']}")
        logger.info(f"Points uploaded:          {stats['points_uploaded']}")

        # Get final collection info
        info = self.vector_store.get_collection_info()
        if info:
            logger.info(f"\nFinal collection stats:")
            logger.info(f"  Total points: {info['points_count']}")
            logger.info(f"  Total vectors: {info['vectors_count']}")

        logger.info("=" * 80)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate embeddings for filing text content"
    )
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Recreate collection (delete existing embeddings)"
    )
    parser.add_argument(
        "--content-type",
        type=str,
        help="Process only specific content type"
    )
    parser.add_argument(
        "--accession",
        type=str,
        help="Process only specific accession number"
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of text sections to process"
    )

    args = parser.parse_args()

    # Get database URL
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logger.error("DATABASE_URL not found in environment")
        sys.exit(1)

    # Get Qdrant URL
    qdrant_url = os.getenv("QDRANT_URL")
    if not qdrant_url:
        logger.error("QDRANT_URL not found in environment")
        sys.exit(1)

    logger.info(f"Database: {database_url[:30]}...")
    logger.info(f"Qdrant: {qdrant_url}")

    # Initialize pipeline
    pipeline = EmbeddingPipeline(database_url)

    # Run pipeline
    try:
        stats = pipeline.run(
            recreate=args.recreate,
            content_type=args.content_type,
            accession=args.accession,
            limit=args.limit
        )

        # Exit with success if we uploaded at least some embeddings
        if stats["points_uploaded"] > 0:
            logger.info("\nPipeline completed successfully!")
            sys.exit(0)
        else:
            logger.warning("\nPipeline completed but no embeddings were uploaded")
            sys.exit(0)

    except KeyboardInterrupt:
        logger.info("\nPipeline interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\nPipeline failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
