"""
RAG (Retrieval Augmented Generation) System

This module provides semantic search capabilities over Form 13F filing text content.

Components:
- embedding_service: Generates vector embeddings using sentence-transformers
- chunker: Splits text into semantically meaningful chunks
- vector_store: Manages Qdrant vector database
- retriever: Retrieves relevant context for queries
"""

from .config import RAGConfig

__all__ = ["RAGConfig"]
