"""
RAG Router

Semantic search endpoints for filing text content.
"""

from fastapi import APIRouter, HTTPException, status
from typing import Optional, List, Dict, Any
import logging

from ..schemas import (
    SemanticSearchRequest,
    SemanticSearchResponse,
    FilingTextResponse
)
from ...tools.rag_tool import RAGRetrievalTool

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize RAG tool (shared across requests)
try:
    rag_tool = RAGRetrievalTool()
    logger.info("RAG tool initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize RAG tool: {e}")
    rag_tool = None


@router.post("/search/semantic", response_model=SemanticSearchResponse)
async def semantic_search(request: SemanticSearchRequest):
    """
    Search Form 13F filing text using semantic search.

    This endpoint uses AI-powered semantic search to find relevant sections
    in Form 13F filings based on meaning, not just keywords.

    **Use this for:**
    - Investment strategies and methodologies
    - Explanatory notes about portfolio changes
    - Manager commentary and disclosures
    - Finding specific information across all filings

    **Example queries:**
    - "What investment strategies are mentioned in filings?"
    - "Are there any explanatory notes about risk management?"
    - "Find filings discussing technology sector investments"

    **Parameters:**
    - `query`: Your search query (3-500 characters)
    - `top_k`: Number of results to return (1-20, default: 5)
    - `filter_accession`: Optional - filter to specific filing
    - `filter_content_type`: Optional - filter to specific content type
      (e.g., "explanatory_notes", "cover_page", "information_table")

    **Returns:**
    - List of matching text sections with relevance scores
    - Each result includes:
      - Text content
      - Accession number (filing ID)
      - Content type (section of filing)
      - Relevance score (0.0-1.0)
    """
    logger.info(f"Semantic search: {request.query[:100]}...")

    if not rag_tool:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Semantic search is currently unavailable. Qdrant vector database may not be running."
        )

    try:
        # Execute semantic search
        result = rag_tool.execute(
            query=request.query,
            top_k=request.top_k,
            filter_accession=request.filter_accession,
            filter_content_type=request.filter_content_type
        )

        if not result.get("success"):
            error_msg = result.get("error", "Unknown error during search")
            logger.error(f"Search failed: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_msg
            )

        logger.info(f"Search completed: {result.get('results_count', 0)} results")

        return SemanticSearchResponse(
            success=True,
            results=result.get("results", []),
            results_count=result.get("results_count", 0),
            query=request.query
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Semantic search error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )


@router.get("/filings/{accession_number}/text", response_model=FilingTextResponse)
async def get_filing_text(
    accession_number: str,
    content_type: Optional[str] = None
):
    """
    Get text content for a specific Form 13F filing.

    Returns all text sections extracted from a filing, or filter to a specific
    content type (e.g., explanatory notes, cover page).

    **Parameters:**
    - `accession_number`: SEC accession number (e.g., "0001067983-25-000001")
    - `content_type`: Optional - filter to specific section type

    **Returns:**
    - Filing metadata (accession number)
    - Text sections organized by content type
    - List of available content types
    """
    logger.info(f"Get filing text: {accession_number}")

    if not rag_tool:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Filing text service is currently unavailable."
        )

    try:
        # Get filing text summary
        result = rag_tool.get_filing_text_summary(accession_number)

        if not result.get("success"):
            error_msg = result.get("error", "Filing not found")
            logger.warning(f"Filing text not found: {accession_number}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_msg
            )

        sections = result.get("sections", {})
        sections_found = result.get("sections_found", [])

        # Filter to specific content type if requested
        if content_type:
            if content_type not in sections:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Content type '{content_type}' not found in this filing"
                )
            sections = {content_type: sections[content_type]}
            sections_found = [content_type]

        logger.info(f"Filing text retrieved: {len(sections_found)} sections")

        return FilingTextResponse(
            success=True,
            accession_number=accession_number,
            sections=sections,
            sections_found=sections_found,
            total_sections=len(sections_found)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get filing text error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve filing text: {str(e)}"
        )
