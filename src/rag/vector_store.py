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
        self.client = QdrantClient(url=config.qdrant_url)

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

        logger.info(f"Collection created successfully")
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
                "vectors_count": info.vectors_count,
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
        batch_size: int = 100
    ) -> int:
        """
        Upload chunks with their embeddings to Qdrant.

        Args:
            chunks: List of text chunks
            embeddings: List of embedding vectors (same order as chunks)
            batch_size: Number of points to upload per batch

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
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            point = PointStruct(
                id=i,  # Will be auto-incremented by Qdrant
                vector=embedding,
                payload={
                    "text": chunk.text,
                    "accession_number": chunk.accession_number,
                    "content_type": chunk.content_type,
                    "chunk_index": chunk.chunk_index,
                    "total_chunks": chunk.total_chunks,
                    "char_start": chunk.char_start,
                    "char_end": chunk.char_end,
                }
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
        filter_content_type: Optional[str] = None
    ) -> List[Dict]:
        """
        Search for similar chunks.

        Args:
            query_embedding: Query vector
            top_k: Number of results to return
            score_threshold: Minimum similarity score
            filter_accession: Filter by accession number
            filter_content_type: Filter by content type

        Returns:
            List of search results with text, metadata, and scores
        """
        # Build filter
        query_filter = None
        if filter_accession or filter_content_type:
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
            formatted_results.append({
                "text": result.payload["text"],
                "accession_number": result.payload["accession_number"],
                "content_type": result.payload["content_type"],
                "chunk_index": result.payload["chunk_index"],
                "total_chunks": result.payload["total_chunks"],
                "score": result.score,
            })

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
