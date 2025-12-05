"""
RAG Semantic Search Tool for LLM Agent

Allows Claude to search through Form 13F filing text content using semantic search.
Finds relevant explanatory notes, investment strategies, and other qualitative information.
"""

from typing import Dict, List, Any, Optional
import logging

from ..rag.config import RAGConfig, get_rag_config
from ..rag.embedding_service import EmbeddingService, get_embedding_service
from ..rag.vector_store import VectorStore, get_vector_store

logger = logging.getLogger(__name__)


class RAGRetrievalTool:
    """
    Tool for semantic search over filing text content.

    Used by LLM agent via function calling to find relevant text from filings.

    Features:
    - Semantic search (meaning-based, not just keywords)
    - Configurable result count
    - Metadata filtering (by filing, content type)
    - Score thresholds for quality
    """

    def __init__(
        self,
        config: Optional[RAGConfig] = None,
        embedding_service: Optional[EmbeddingService] = None,
        vector_store: Optional[VectorStore] = None
    ):
        """
        Initialize RAG retrieval tool.

        Args:
            config: RAG configuration (optional, loads from env if not provided)
            embedding_service: Embedding service instance (optional)
            vector_store: Vector store instance (optional)
        """
        self.config = config or get_rag_config()

        # Initialize components
        self.embedding_service = embedding_service or get_embedding_service(self.config)
        self.vector_store = vector_store or get_vector_store(self.config)

        logger.info("RAG retrieval tool initialized")

    def get_tool_definition(self) -> Dict[str, Any]:
        """
        Get tool definition for LLM function calling.

        Returns Anthropic-compatible tool definition.

        Returns:
            Tool definition dict
        """
        return {
            "type": "function",
            "function": {
                "name": "search_filing_text",
                "description": """Search through Form 13F filing text content using semantic search.

IMPORTANT: Form 13F filings are regulatory documents that report holdings. They typically
do NOT contain detailed investment strategies, philosophies, or market commentary.

Best use cases:
- Manager contact information and addresses
- Amendment notices and explanations
- Regulatory disclosures about fund structure
- Information about relying advisers or third-party management
- Filing corrections or updates

Limited/No data for:
- Investment strategies or philosophies (not in 13F filings)
- Investment theses or rationales (not required by SEC)
- Market commentary or analysis (not in 13F filings)
- Future investment plans (not disclosed in 13F)

The search understands meaning, not just keywords. Returns the most relevant text excerpts
with their source filings.

Content types available:
- cover_page_info: Filing manager contact details and basic info
- explanatory_notes: Regulatory disclosures, fund structure notes, amendments
- amendment_info: Reasons for filing amendments
- other_documents: Additional exhibits and disclosures

For analyzing holdings data (positions, values, shares, portfolio composition),
use the query_database tool instead - that's where the actual investment data is.
""",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Natural language search query describing what text to find"
                        },
                        "top_k": {
                            "type": "integer",
                            "description": f"Number of results to return (1-10, default: {self.config.top_k})",
                            "minimum": 1,
                            "maximum": 10,
                            "default": self.config.top_k
                        },
                        "filter_accession": {
                            "type": "string",
                            "description": "Optional: Filter results to specific filing accession number"
                        },
                        "filter_content_type": {
                            "type": "string",
                            "description": "Optional: Filter by content type (cover_page_info, explanatory_notes, amendment_info, other_documents)",
                            "enum": ["cover_page_info", "explanatory_notes", "amendment_info", "other_documents"]
                        }
                    },
                    "required": ["query"]
                }
            }
        }

    def execute(
        self,
        query: str,
        top_k: Optional[int] = None,
        filter_accession: Optional[str] = None,
        filter_content_type: Optional[str] = None,
        filter_cik_company: Optional[str] = None,
        filter_section: Optional[str] = None,
        filter_year: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Execute semantic search query.

        Args:
            query: Natural language search query
            top_k: Number of results to return (1-10)
            filter_accession: Filter to specific filing
            filter_content_type: Filter by content type
            filter_cik_company: Filter to specific company CIK (10-K)
            filter_section: Filter to specific 10-K section (e.g., "Item 1A")
            filter_year: Filter to specific filing year

        Returns:
            Dictionary with results and metadata
        """
        try:
            # Validate and set defaults
            if not query or not query.strip():
                return {
                    "success": False,
                    "error": "Query cannot be empty",
                    "results": []
                }

            top_k = top_k or self.config.top_k
            top_k = max(1, min(10, top_k))  # Clamp to 1-10

            logger.info(f"RAG search query: '{query}' (top_k={top_k})")

            # Generate query embedding
            query_embedding = self.embedding_service.get_query_embedding(query)

            # Search vector store
            results = self.vector_store.search(
                query_embedding=query_embedding,
                top_k=top_k,
                score_threshold=self.config.score_threshold,
                filter_accession=filter_accession,
                filter_content_type=filter_content_type,
                filter_cik_company=filter_cik_company,
                filter_section=filter_section,
                filter_year=filter_year
            )

            # Format results for LLM
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "text": result["text"],
                    "accession_number": result["accession_number"],
                    "content_type": result["content_type"],
                    "relevance_score": round(result["score"], 3),
                    "chunk_info": f"{result['chunk_index'] + 1}/{result['total_chunks']}"
                })

            # Build filters_applied dict
            filters_applied = {}
            if filter_accession:
                filters_applied["accession"] = filter_accession
            if filter_content_type:
                filters_applied["content_type"] = filter_content_type
            if filter_cik_company:
                filters_applied["cik_company"] = filter_cik_company
            if filter_section:
                filters_applied["section"] = filter_section
            if filter_year:
                filters_applied["year"] = filter_year

            return {
                "success": True,
                "query": query,
                "results_count": len(formatted_results),
                "results": formatted_results,
                "filters_applied": filters_applied if filters_applied else None
            }

        except Exception as e:
            logger.error(f"RAG search error: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Search failed: {str(e)}",
                "results": []
            }

    def get_filing_text_summary(self, accession_number: str) -> Dict[str, Any]:
        """
        Get all text content for a specific filing.

        Useful after SQL query identifies a filing of interest.

        Args:
            accession_number: Filing accession number

        Returns:
            Dictionary with all text sections for the filing
        """
        try:
            # Search with very low threshold to get all chunks for this filing
            dummy_query_embedding = self.embedding_service.get_query_embedding("filing information")

            results = self.vector_store.search(
                query_embedding=dummy_query_embedding,
                top_k=100,  # Get all chunks
                score_threshold=0.0,  # No threshold
                filter_accession=accession_number
            )

            # Group by content type
            sections = {}
            for result in results:
                content_type = result["content_type"]
                if content_type not in sections:
                    sections[content_type] = []
                sections[content_type].append(result["text"])

            # Combine chunks for each content type
            combined_sections = {}
            for content_type, texts in sections.items():
                combined_sections[content_type] = " ".join(texts)

            return {
                "success": True,
                "accession_number": accession_number,
                "sections_found": list(combined_sections.keys()),
                "sections": combined_sections
            }

        except Exception as e:
            logger.error(f"Error getting filing summary: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "sections": {}
            }


def create_rag_tool(
    config: Optional[RAGConfig] = None
) -> RAGRetrievalTool:
    """
    Factory function to create RAG tool instance.

    Args:
        config: Optional RAG configuration

    Returns:
        RAGRetrievalTool instance
    """
    return RAGRetrievalTool(config=config)
