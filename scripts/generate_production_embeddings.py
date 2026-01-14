"""
Generate embeddings for production filing text content.

This connects to production database and Qdrant Cloud to generate embeddings.

Usage:
    export DATABASE_URL="postgresql://..."
    export QDRANT_URL="https://..."
    export QDRANT_API_KEY="..."
    python scripts/generate_production_embeddings.py
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy import text as sql_text
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer
import logging
from tqdm import tqdm

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_embeddings(batch_size=100, recreate=False):
    """Generate embeddings for all filing text content."""

    # Get environment variables
    database_url = os.getenv("DATABASE_URL")
    qdrant_url = os.getenv("QDRANT_URL")
    qdrant_api_key = os.getenv("QDRANT_API_KEY")

    if not database_url:
        logger.error("❌ DATABASE_URL not set")
        return False
    if not qdrant_url:
        logger.error("❌ QDRANT_URL not set")
        return False

    logger.info("Connecting to database...")
    db_engine = create_engine(database_url)

    logger.info(f"Connecting to Qdrant at {qdrant_url}...")
    qdrant_client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)

    # Load embedding model
    logger.info("Loading sentence-transformers model...")
    model = SentenceTransformer('all-MiniLM-L6-v2')
    vector_size = 384

    collection_name = "filing_text_embeddings"

    # Create or recreate collection
    collections = qdrant_client.get_collections().collections
    collection_exists = any(c.name == collection_name for c in collections)

    if recreate and collection_exists:
        logger.info(f"Deleting existing collection: {collection_name}")
        qdrant_client.delete_collection(collection_name)
        collection_exists = False

    if not collection_exists:
        logger.info(f"Creating collection: {collection_name}")
        qdrant_client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )

    # Get all text content from database
    logger.info("Fetching text content from database...")
    with db_engine.connect() as conn:
        result = conn.execute(sql_text("""
            SELECT
                ftc.id,
                ftc.accession_number,
                ftc.content_type,
                ftc.text_content,
                f.cik,
                f.period_of_report,
                m.name as manager_name
            FROM filing_text_content ftc
            JOIN filings f ON ftc.accession_number = f.accession_number
            JOIN managers m ON f.cik = m.cik
            ORDER BY ftc.id
        """))

        rows = result.fetchall()
        logger.info(f"Found {len(rows)} text sections to embed")

    # Get existing points to skip duplicates
    existing_points = set()
    if collection_exists:
        logger.info("Checking for existing embeddings...")
        scroll_result = qdrant_client.scroll(
            collection_name=collection_name,
            limit=10000,  # Adjust if you have more
            with_payload=False,
            with_vectors=False
        )
        existing_points = {point.id for point in scroll_result[0]}
        logger.info(f"Found {len(existing_points)} existing embeddings")

    # Generate embeddings in batches
    points_to_upload = []
    skipped = 0

    for i in tqdm(range(0, len(rows), batch_size), desc="Generating embeddings"):
        batch = rows[i:i+batch_size]

        for row in batch:
            point_id = row[0]  # id column

            # Skip if already exists
            if point_id in existing_points:
                skipped += 1
                continue

            # Generate embedding
            text = row[3]  # text_content
            embedding = model.encode(text, convert_to_tensor=False).tolist()

            # Create point with metadata
            point = PointStruct(
                id=point_id,
                vector=embedding,
                payload={
                    "accession_number": row[1],
                    "content_type": row[2],
                    "text_preview": text[:200],
                    "cik": row[4],
                    "period_of_report": str(row[5]),
                    "manager_name": row[6],
                }
            )
            points_to_upload.append(point)

        # Upload batch
        if points_to_upload:
            qdrant_client.upsert(
                collection_name=collection_name,
                points=points_to_upload
            )
            points_to_upload = []

    # Upload any remaining points
    if points_to_upload:
        qdrant_client.upsert(
            collection_name=collection_name,
            points=points_to_upload
        )

    # Get final count
    collection_info = qdrant_client.get_collection(collection_name)
    total_embeddings = collection_info.points_count

    logger.info(f"\n✅ Embedding generation complete!")
    logger.info(f"   Total embeddings in Qdrant: {total_embeddings}")
    logger.info(f"   Skipped (already existed): {skipped}")
    logger.info(f"   Newly created: {total_embeddings - len(existing_points)}")

    return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate embeddings for production")
    parser.add_argument("--batch-size", type=int, default=100, help="Batch size for processing")
    parser.add_argument("--recreate", action="store_true", help="Recreate collection (delete existing)")

    args = parser.parse_args()

    success = generate_embeddings(batch_size=args.batch_size, recreate=args.recreate)
    sys.exit(0 if success else 1)
