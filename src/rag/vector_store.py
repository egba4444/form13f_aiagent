"""
Vector Store Interface for Qdrant

Manages storage and retrieval of embeddings in Qdrant vector database.

Features:
- Collection management (create, delete, info)
- Batch upload of embeddings with metadata
- Similarity search
- Filtering by metadata (accession number, content type, etc.)
"""

import logging
import uuid
from typing import List, Dict, Optional
from dataclasses import asdict

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    SearchParams
)

from .config import RAGConfig
from .chunker import TextChunk

logger = logging.getLogger(__name__)


class VectorStore:
    """Interface to Qdrant vector database."""

    def __init__(self, config: RAGConfig):
        """
        Initialize vector store.

        Args:
            config: RAG configuration
        """
        self.config = config
        self.collection_name = config.qdrant_collection_name
        self.dimension = config.embedding_dimension

        logger.info(f"Connecting to Qdrant at {config.qdrant_url}")
        logger.info(f"Qdrant API key configured: {bool(config.qdrant_api_key)}")
        self.client = QdrantClient(
            url=config.qdrant_url,
            api_key=config.qdrant_api_key
        )

        logger.info(f"Using collection: {self.collection_name}")

    def create_collection(self, recreate: bool = False) -> bool:
        """
        Create the collection for filing text embeddings.

        Args:
            recreate: If True, delete existing collection and recreate

        Returns:
            True if collection was created, False if already existed
        """
        # Check if collection exists
        collections = self.client.get_collections().collections
        collection_names = [c.name for c in collections]

        if self.collection_name in collection_names:
            if recreate:
                logger.warning(f"Deleting existing collection: {self.collection_name}")
                self.client.delete_collection(self.collection_name)
            else:
                logger.info(f"Collection already exists: {self.collection_name}")
                return False

        # Create collection
        logger.info(f"Creating collection: {self.collection_name}")
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(
                size=self.dimension,
                distance=Distance.COSINE  # Cosine similarity
            )
        )

        # Create payload indexes for filtering
        logger.info("Creating payload indexes for filtering...")
        from qdrant_client.models import PayloadSchemaType

        # Index for accession_number (used for filtering by filing)
        self.client.create_payload_index(
            collection_name=self.collection_name,
            field_name="accession_number",
            field_schema=PayloadSchemaType.KEYWORD
        )

        # Index for content_type (used for filtering by section type)
        self.client.create_payload_index(
            collection_name=self.collection_name,
            field_name="content_type",
            field_schema=PayloadSchemaType.KEYWORD
        )

        # Index for cik_company (used for filtering by company - 10-K)
        self.client.create_payload_index(
            collection_name=self.collection_name,
            field_name="cik_company",
            field_schema=PayloadSchemaType.KEYWORD
        )

        # Index for section_name (used for filtering by 10-K section)
        self.client.create_payload_index(
            collection_name=self.collection_name,
            field_name="section_name",
            field_schema=PayloadSchemaType.KEYWORD
        )

        # Index for filing_year (used for filtering by year)
        self.client.create_payload_index(
            collection_name=self.collection_name,
            field_name="filing_year",
            field_schema=PayloadSchemaType.INTEGER
        )

        logger.info(f"Collection created successfully with payload indexes")
        return True

    def delete_collection(self) -> bool:
        """
        Delete the collection.

        Returns:
            True if deleted, False if didn't exist
        """
        try:
            self.client.delete_collection(self.collection_name)
            logger.info(f"Deleted collection: {self.collection_name}")
            return True
        except Exception as e:
            logger.error(f"Error deleting collection: {e}")
            return False

    def clear_collection(self) -> bool:
        """
        Clear all data from collection and recreate it.

        This is useful when switching from 13F to 10-K data, as it removes
        all existing embeddings and recreates the collection with fresh indexes.

        Returns:
            True if successful
        """
        logger.warning(f"Clearing collection: {self.collection_name}")
        self.delete_collection()
        self.create_collection()
        logger.info(f"Collection cleared and recreated successfully")
        return True

    def get_collection_info(self) -> Optional[Dict]:
        """
        Get information about the collection.

        Returns:
            Dictionary with collection info, or None if doesn't exist
        """
        try:
            info = self.client.get_collection(self.collection_name)
            return {
                "name": self.collection_name,
                "points_count": info.points_count,
                "status": info.status,
            }
        except Exception as e:
            logger.error(f"Error getting collection info: {e}")
            return None

    def upload_chunks(
        self,
        chunks: List[TextChunk],
        embeddings: List[List[float]],
        batch_size: int = 100,
        cik_company: Optional[str] = None,
        filing_year: Optional[int] = None,
        section_name: Optional[str] = None
    ) -> int:
        """
        Upload chunks with their embeddings to Qdrant.

        Args:
            chunks: List of text chunks
            embeddings: List of embedding vectors (same order as chunks)
            batch_size: Number of points to upload per batch
            cik_company: CIK of the company (for 10-K filings)
            filing_year: Year of the filing (e.g., 2023)
            section_name: 10-K section name (e.g., "Item 1A")

        Returns:
            Number of points uploaded
        """
        if len(chunks) != len(embeddings):
            raise ValueError("Number of chunks must match number of embeddings")

        if not chunks:
            return 0

        logger.info(f"Uploading {len(chunks)} chunks to Qdrant...")

        # Prepare points for upload
        points = []
        for chunk, embedding in zip(chunks, embeddings):
            payload = {
                "text": chunk.text,
                "accession_number": chunk.accession_number,
                "content_type": chunk.content_type,
                "chunk_index": chunk.chunk_index,
                "total_chunks": chunk.total_chunks,
                "char_start": chunk.char_start,
                "char_end": chunk.char_end,
            }

            # Add 10-K specific metadata if provided
            if cik_company:
                payload["cik_company"] = cik_company
            if filing_year:
                payload["filing_year"] = filing_year
            if section_name:
                payload["section_name"] = section_name

            point = PointStruct(
                id=str(uuid.uuid4()),  # Use UUID to avoid ID collisions
                vector=embedding,
                payload=payload
            )
            points.append(point)

        # Upload in batches
        total_uploaded = 0
        for i in range(0, len(points), batch_size):
            batch = points[i:i + batch_size]
            self.client.upsert(
                collection_name=self.collection_name,
                points=batch
            )
            total_uploaded += len(batch)
            logger.info(f"Uploaded {total_uploaded}/{len(points)} points")

        logger.info(f"Successfully uploaded {total_uploaded} chunks")
        return total_uploaded

    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        score_threshold: Optional[float] = None,
        filter_accession: Optional[str] = None,
        filter_content_type: Optional[str] = None,
        filter_cik_company: Optional[str] = None,
        filter_section: Optional[str] = None,
        filter_year: Optional[int] = None
    ) -> List[Dict]:
        """
        Search for similar chunks.

        Args:
            query_embedding: Query vector
            top_k: Number of results to return
            score_threshold: Minimum similarity score
            filter_accession: Filter by accession number
            filter_content_type: Filter by content type
            filter_cik_company: Filter by company CIK (10-K)
            filter_section: Filter by section name (10-K, e.g. "Item 1A")
            filter_year: Filter by filing year (10-K)

        Returns:
            List of search results with text, metadata, and scores
        """
        # Build filter
        query_filter = None
        conditions = []

        if filter_accession:
            conditions.append(
                FieldCondition(
                    key="accession_number",
                    match=MatchValue(value=filter_accession)
                )
            )

        if filter_content_type:
            conditions.append(
                FieldCondition(
                    key="content_type",
                    match=MatchValue(value=filter_content_type)
                )
            )

        if filter_cik_company:
            conditions.append(
                FieldCondition(
                    key="cik_company",
                    match=MatchValue(value=filter_cik_company)
                )
            )

        if filter_section:
            conditions.append(
                FieldCondition(
                    key="section_name",
                    match=MatchValue(value=filter_section)
                )
            )

        if filter_year:
            conditions.append(
                FieldCondition(
                    key="filing_year",
                    match=MatchValue(value=filter_year)
                )
            )

        if conditions:
            query_filter = Filter(must=conditions)

        # Search (using query_points for newer Qdrant client)
        results = self.client.query_points(
            collection_name=self.collection_name,
            query=query_embedding,
            limit=top_k,
            query_filter=query_filter,
            score_threshold=score_threshold,
            with_payload=True
        ).points

        # Format results
        formatted_results = []
        for result in results:
            result_dict = {
                "text": result.payload["text"],
                "accession_number": result.payload["accession_number"],
                "content_type": result.payload["content_type"],
                "chunk_index": result.payload["chunk_index"],
                "total_chunks": result.payload["total_chunks"],
                "score": result.score,
            }

            # Add 10-K metadata if present
            if "cik_company" in result.payload:
                result_dict["cik_company"] = result.payload["cik_company"]
            if "section_name" in result.payload:
                result_dict["section_name"] = result.payload["section_name"]
            if "filing_year" in result.payload:
                result_dict["filing_year"] = result.payload["filing_year"]

            formatted_results.append(result_dict)

        return formatted_results

    def count_points(self) -> int:
        """
        Count total points in collection.

        Returns:
            Number of points
        """
        try:
            info = self.client.get_collection(self.collection_name)
            return info.points_count or 0
        except Exception:
            return 0


def get_vector_store(config: Optional[RAGConfig] = None) -> VectorStore:
    """
    Get vector store instance.

    Args:
        config: RAG configuration (optional)

    Returns:
        VectorStore instance
    """
    if config is None:
        from .config import get_rag_config
        config = get_rag_config()

    return VectorStore(config)
