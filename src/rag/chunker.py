"""
Text Chunking for RAG

Splits long text documents into smaller, semantically meaningful chunks
that can be embedded and retrieved independently.

Strategy:
- Split on paragraph boundaries first
- If paragraphs are too long, split on sentence boundaries
- Maintain overlap between chunks for context continuity
- Preserve metadata (accession number, content type, etc.)
"""

import re
from typing import List, Dict
from dataclasses import dataclass

from .config import RAGConfig


@dataclass
class TextChunk:
    """A chunk of text with metadata."""
    text: str
    accession_number: str
    content_type: str
    chunk_index: int
    total_chunks: int
    char_start: int
    char_end: int


class TextChunker:
    """Splits text into overlapping chunks for embedding."""

    def __init__(self, config: RAGConfig):
        """
        Initialize chunker.

        Args:
            config: RAG configuration
        """
        self.config = config
        self.chunk_size = config.chunk_size
        self.chunk_overlap = config.chunk_overlap
        self.min_chunk_size = config.min_chunk_size

    def chunk_text(
        self,
        text: str,
        accession_number: str,
        content_type: str
    ) -> List[TextChunk]:
        """
        Split text into chunks with overlap.

        Args:
            text: Text to chunk
            accession_number: Filing accession number
            content_type: Type of content (e.g., "explanatory_notes")

        Returns:
            List of TextChunk objects
        """
        # Clean text
        text = self._clean_text(text)

        if len(text) < self.min_chunk_size:
            # Text is too short to chunk
            return []

        # Try paragraph-based chunking first
        paragraphs = self._split_paragraphs(text)

        chunks = []
        current_chunk = ""
        char_start = 0

        for para in paragraphs:
            # If adding this paragraph would exceed chunk size
            if len(current_chunk) + len(para) > self.chunk_size and current_chunk:
                # Save current chunk
                chunks.append(current_chunk.strip())
                # Start new chunk with overlap
                overlap_text = self._get_overlap(current_chunk)
                char_start = len(current_chunk) - len(overlap_text)
                current_chunk = overlap_text + para
            else:
                current_chunk += para

        # Add final chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        # If we still have chunks that are too long, split on sentences
        final_chunks = []
        for chunk in chunks:
            if len(chunk) > self.chunk_size:
                final_chunks.extend(self._split_by_sentences(chunk))
            else:
                final_chunks.append(chunk)

        # Filter out chunks that are too small
        final_chunks = [c for c in final_chunks if len(c) >= self.min_chunk_size]

        # Create TextChunk objects with metadata
        result = []
        total_chunks = len(final_chunks)

        char_position = 0
        for i, chunk_text in enumerate(final_chunks):
            chunk_obj = TextChunk(
                text=chunk_text,
                accession_number=accession_number,
                content_type=content_type,
                chunk_index=i,
                total_chunks=total_chunks,
                char_start=char_position,
                char_end=char_position + len(chunk_text)
            )
            result.append(chunk_obj)
            char_position += len(chunk_text)

        return result

    def _clean_text(self, text: str) -> str:
        """Clean text by removing extra whitespace."""
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove leading/trailing whitespace
        text = text.strip()
        return text

    def _split_paragraphs(self, text: str) -> List[str]:
        """Split text on paragraph boundaries."""
        # Split on double newlines (paragraph breaks)
        paragraphs = re.split(r'\n\s*\n', text)

        # Clean and filter
        paragraphs = [p.strip() + ' ' for p in paragraphs if p.strip()]

        return paragraphs

    def _split_by_sentences(self, text: str) -> List[str]:
        """Split long text by sentences."""
        # Simple sentence splitting (can be improved with NLTK/spaCy)
        sentences = re.split(r'(?<=[.!?])\s+', text)

        chunks = []
        current_chunk = ""

        for sentence in sentences:
            if len(current_chunk) + len(sentence) > self.chunk_size and current_chunk:
                chunks.append(current_chunk.strip())
                # Start new chunk with overlap
                overlap = self._get_overlap(current_chunk)
                current_chunk = overlap + sentence
            else:
                current_chunk += sentence + " "

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks

    def _get_overlap(self, text: str) -> str:
        """
        Get overlap text from end of chunk.

        Args:
            text: Text to get overlap from

        Returns:
            Last N characters based on overlap setting
        """
        if len(text) <= self.chunk_overlap:
            return text

        # Get last chunk_overlap characters
        overlap = text[-self.chunk_overlap:]

        # Try to start at a word boundary
        space_idx = overlap.find(' ')
        if space_idx != -1:
            overlap = overlap[space_idx + 1:]

        return overlap


def chunk_filing_content(
    content_rows: List[Dict],
    config: RAGConfig
) -> List[TextChunk]:
    """
    Chunk multiple filing content rows.

    Args:
        content_rows: List of dicts with keys: text_content, accession_number, content_type
        config: RAG configuration

    Returns:
        List of all chunks from all content rows
    """
    chunker = TextChunker(config)
    all_chunks = []

    for row in content_rows:
        chunks = chunker.chunk_text(
            text=row["text_content"],
            accession_number=row["accession_number"],
            content_type=row["content_type"]
        )
        all_chunks.extend(chunks)

    return all_chunks
