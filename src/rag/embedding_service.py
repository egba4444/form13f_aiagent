"""
Embedding Service

Generates vector embeddings for text using sentence-transformers.

Model: all-MiniLM-L6-v2
- Lightweight (22M parameters)
- Fast inference
- Good quality for semantic search
- 384-dimensional embeddings
- Free (no API costs)

Alternative models:
- all-mpnet-base-v2 (768 dims, better quality, slower)
- all-MiniLM-L12-v2 (384 dims, better than L6)
"""

import logging
from typing import List, Optional
import numpy as np

from sentence_transformers import SentenceTransformer

from .config import RAGConfig

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating text embeddings."""

    def __init__(self, config: RAGConfig):
        """
        Initialize embedding service.

        Args:
            config: RAG configuration
        """
        self.config = config
        self.model_name = config.embedding_model
        self.batch_size = config.embedding_batch_size
        self.dimension = config.embedding_dimension

        logger.info(f"Loading embedding model: {self.model_name}")

        # Load model
        device = "cuda" if config.use_gpu else "cpu"
        self.model = SentenceTransformer(
            self.model_name,
            device=device
        )

        logger.info(f"Model loaded on device: {device}")
        logger.info(f"Embedding dimension: {self.dimension}")

    def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector as list of floats
        """
        embedding = self.model.encode(
            text,
            convert_to_numpy=True,
            show_progress_bar=False
        )
        return embedding.tolist()

    def embed_batch(
        self,
        texts: List[str],
        show_progress: bool = True
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed
            show_progress: Show progress bar

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        logger.info(f"Embedding {len(texts)} texts in batches of {self.batch_size}")

        embeddings = self.model.encode(
            texts,
            batch_size=self.batch_size,
            convert_to_numpy=True,
            show_progress_bar=show_progress
        )

        # Convert to list of lists
        return embeddings.tolist()

    def get_query_embedding(self, query: str) -> List[float]:
        """
        Generate embedding for a search query.

        Args:
            query: Search query text

        Returns:
            Query embedding vector
        """
        # For sentence-transformers, query and document embeddings
        # are generated the same way
        return self.embed_text(query)

    def similarity(
        self,
        embedding1: List[float],
        embedding2: List[float]
    ) -> float:
        """
        Calculate cosine similarity between two embeddings.

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector

        Returns:
            Cosine similarity score (0-1)
        """
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)

        # Cosine similarity
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        similarity = dot_product / (norm1 * norm2)
        return float(similarity)


def get_embedding_service(config: Optional[RAGConfig] = None) -> EmbeddingService:
    """
    Get embedding service instance.

    Args:
        config: RAG configuration (optional, will load from env if not provided)

    Returns:
        EmbeddingService instance
    """
    if config is None:
        from .config import get_rag_config
        config = get_rag_config()

    return EmbeddingService(config)
