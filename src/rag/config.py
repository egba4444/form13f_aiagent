"""
RAG System Configuration

Centralized configuration for all RAG components including:
- Embedding model settings
- Vector database settings
- Chunking parameters
- Retrieval parameters
"""

import os
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class RAGConfig(BaseSettings):
    """Configuration for RAG system."""

    # Qdrant Vector Database
    qdrant_url: str = Field(
        default="http://localhost:6333",
        description="Qdrant server URL"
    )
    qdrant_api_key: Optional[str] = Field(
        default=None,
        description="Qdrant API key (for cloud deployments)"
    )
    qdrant_collection_name: str = Field(
        default="filing_text_embeddings",
        description="Name of the Qdrant collection"
    )

    # Embedding Model
    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        description="HuggingFace model for embeddings"
    )
    embedding_dimension: int = Field(
        default=384,
        description="Dimension of embedding vectors (all-MiniLM-L6-v2 = 384)"
    )
    embedding_batch_size: int = Field(
        default=32,
        description="Batch size for embedding generation"
    )

    # Text Chunking
    chunk_size: int = Field(
        default=500,
        description="Maximum characters per chunk"
    )
    chunk_overlap: int = Field(
        default=50,
        description="Overlap between chunks in characters"
    )
    min_chunk_size: int = Field(
        default=100,
        description="Minimum chunk size to keep"
    )

    # Retrieval
    top_k: int = Field(
        default=5,
        description="Number of similar chunks to retrieve"
    )
    score_threshold: float = Field(
        default=0.5,
        description="Minimum similarity score threshold"
    )

    # Performance
    use_gpu: bool = Field(
        default=False,
        description="Use GPU for embeddings if available"
    )

    class Config:
        env_prefix = "RAG_"
        case_sensitive = False


def get_rag_config() -> RAGConfig:
    """Get RAG configuration from environment."""
    # Override qdrant_url from QDRANT_URL if available
    qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
    qdrant_api_key = os.getenv("QDRANT_API_KEY")
    return RAGConfig(qdrant_url=qdrant_url, qdrant_api_key=qdrant_api_key)
