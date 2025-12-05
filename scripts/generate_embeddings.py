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

    # Clear collection first (recommended for 10-K migration)
    python scripts/generate_embeddings.py --clear-first

    # Process only 10-K filings
    python scripts/generate_embeddings.py --filing-type 10-K

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
        logger.info(f"Chunk size (13F): {self.config.chunk_size}")
        logger.info(f"Chunk size (10-K): {self.config.chunk_size_10k}")
        logger.info(f"Chunk overlap: {self.config.chunk_overlap}")

    def fetch_text_content(
        self,
        filing_type: Optional[str] = None,
        content_type: Optional[str] = None,
        accession: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        Fetch text content from database.

        Args:
            filing_type: Filter by filing type (10-K, 13F-HR, etc.)
            content_type: Filter by content type
            accession: Filter by accession number
            limit: Limit number of rows

        Returns:
            List of dicts with text_content, accession_number, content_type, and 10-K metadata
        """
        conn = psycopg2.connect(self.database_url)
        cur = conn.cursor()

        # Build query - include 10-K metadata fields
        query = """
            SELECT
                accession_number,
                content_type,
                text_content,
                filing_type,
                cik_company,
                section_name,
                EXTRACT(YEAR FROM extracted_at) as filing_year
            FROM filing_text_content
            WHERE 1=1
        """
        params = []

        if filing_type:
            query += " AND filing_type = %s"
            params.append(filing_type)

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
                "text_content": row[2],
                "filing_type": row[3],
                "cik_company": row[4],
                "section_name": row[5],
                "filing_year": int(row[6]) if row[6] else None
            })

        cur.close()
        conn.close()

        logger.info(f"Fetched {len(results)} text sections from database")
        return results

    def run(
        self,
        recreate: bool = False,
        clear_first: bool = False,
        filing_type: Optional[str] = None,
        content_type: Optional[str] = None,
        accession: Optional[str] = None,
        limit: Optional[int] = None
    ) -> Dict[str, int]:
        """
        Run the complete embedding generation pipeline.

        Args:
            recreate: Recreate collection (delete existing) - deprecated, use clear_first
            clear_first: Clear collection before processing (recommended for 10-K migration)
            filing_type: Filter by filing type (10-K, 13F-HR, etc.)
            content_type: Filter by content type
            accession: Filter by accession number
            limit: Limit number of text sections to process

        Returns:
            Dictionary with statistics
        """
        # clear_first takes precedence over recreate
        should_clear = clear_first or recreate
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
        if should_clear:
            logger.info("Clearing collection (removing all existing embeddings)...")
            self.vector_store.clear_collection()
        else:
            self.vector_store.create_collection(recreate=False)

        collection_info = self.vector_store.get_collection_info()
        if collection_info:
            logger.info(f"Collection: {collection_info['name']}")
            logger.info(f"Existing points: {collection_info['points_count']}")

        # Step 2: Fetch text content
        logger.info("\nStep 2: Fetching text content from database...")
        content_rows = self.fetch_text_content(
            filing_type=filing_type,
            content_type=content_type,
            accession=accession,
            limit=limit
        )
        stats["text_sections"] = len(content_rows)

        # Determine if we're processing 10-K or 13F data
        is_10k = filing_type == "10-K" or (
            content_rows and content_rows[0].get("filing_type") == "10-K"
        )

        if not content_rows:
            logger.warning("No text content found. Exiting.")
            return stats

        # Step 3: Chunk text
        logger.info("\nStep 3: Chunking text...")

        # Use appropriate chunk size for filing type
        original_chunk_size = self.config.chunk_size
        if is_10k:
            logger.info(f"Using 10-K chunk size: {self.config.chunk_size_10k} chars")
            self.config.chunk_size = self.config.chunk_size_10k

        chunks = chunk_filing_content(content_rows, self.config)

        # Restore original chunk size
        self.config.chunk_size = original_chunk_size

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

        if is_10k:
            # For 10-K, we need to upload in batches with metadata per chunk
            # Group chunks by their metadata (cik_company, section_name, filing_year)
            logger.info("Uploading 10-K chunks with metadata...")

            # Create a map from accession_number to metadata
            metadata_map = {}
            for row in content_rows:
                metadata_map[row["accession_number"]] = {
                    "cik_company": row.get("cik_company"),
                    "section_name": row.get("section_name"),
                    "filing_year": row.get("filing_year")
                }

            # Upload in batches, but we need to group by metadata
            batch_size = 100
            total_uploaded = 0

            for i in range(0, len(chunks), batch_size):
                batch_chunks = chunks[i:i + batch_size]
                batch_embeddings = embeddings[i:i + batch_size]

                # For simplicity, use metadata from first chunk in batch
                # (In practice, all chunks in 10-K should have same metadata per section)
                first_chunk = batch_chunks[0]
                metadata = metadata_map.get(first_chunk.accession_number, {})

                uploaded_batch = self.vector_store.upload_chunks(
                    chunks=batch_chunks,
                    embeddings=batch_embeddings,
                    batch_size=batch_size,
                    cik_company=metadata.get("cik_company"),
                    filing_year=metadata.get("filing_year"),
                    section_name=metadata.get("section_name")
                )
                total_uploaded += uploaded_batch

            stats["points_uploaded"] = total_uploaded
        else:
            # For 13F, upload without 10-K metadata
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
            logger.info(f"  Status: {info['status']}")

        logger.info("=" * 80)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate embeddings for filing text content"
    )
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Recreate collection (delete existing embeddings) - DEPRECATED, use --clear-first"
    )
    parser.add_argument(
        "--clear-first",
        action="store_true",
        help="Clear collection before processing (recommended for 10-K migration)"
    )
    parser.add_argument(
        "--filing-type",
        type=str,
        choices=["10-K", "13F-HR"],
        help="Process only specific filing type (10-K or 13F-HR)"
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
            clear_first=args.clear_first,
            filing_type=args.filing_type,
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
