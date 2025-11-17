"""
Query Router

Natural language query endpoint for the AI agent.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Header
from fastapi.responses import JSONResponse
from typing import Optional
import logging
import time
import os

from ..schemas import QueryRequest, QueryResponse
from ..dependencies import get_database_url
from ...agent import Agent
from ...agent.llm_config import LLMClient
from ..analytics import analytics
from ..cache import query_cache
from ...auth.supabase_client import verify_token

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/query", response_model=QueryResponse)
async def query_agent(
    request: QueryRequest,
    authorization: Optional[str] = Header(None)
):
    """
    Ask a natural language question about Form 13F data.

    The agent will:
    1. Understand your question
    2. Generate safe SQL query
    3. Execute on database
    4. Format natural language answer

    **Authentication (Optional):**
    - If authenticated with Bearer token, enables watchlist features
    - Allows agent to add managers/securities to your watchlist

    **Example questions:**
    - "How many Apple shares did Berkshire Hathaway hold in Q4 2024?"
    - "What are the top 5 managers by portfolio value?"
    - "Who holds the most Tesla stock?"
    - "Add Berkshire Hathaway to my watchlist" (requires authentication)

    **Parameters:**
    - `query`: Your natural language question (3-500 characters)
    - `include_sql`: Include generated SQL in response (default: false)
    - `include_raw_data`: Include raw query results (default: false)

    **Returns:**
    - Natural language answer
    - Optional: Generated SQL query
    - Optional: Raw database results
    - Execution time and metadata
    """
    logger.info(f"Query received: {request.query[:100]}...")
    start_time = time.time()

    # Extract and verify auth token if provided
    user_id = None
    if authorization:
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            auth_token = parts[1]
            # Verify token and extract user_id
            user_info = verify_token(auth_token)
            if user_info:
                user_id = user_info.get("id")
                logger.info(f"Authenticated user: {user_id}")
            else:
                logger.warning("Invalid auth token provided")

    # Create agent with optional user_id for watchlist features
    database_url = get_database_url()
    llm_client = LLMClient()
    agent = Agent(
        database_url,
        llm_client=llm_client,
        verbose=False,
        user_id=user_id
    )

    try:
        # Check cache first
        cached_response = query_cache.get(request.query)
        if cached_response:
            logger.info(f"Cache hit for query: {request.query[:100]}...")
            response_time_ms = int((time.time() - start_time) * 1000)

            # Record analytics
            analytics.record_query(
                query=request.query,
                response_time_ms=response_time_ms,
                success=True
            )

            return QueryResponse(**cached_response)

        # Convert conversation history to dict format
        conversation_history = None
        if request.conversation_history:
            conversation_history = [
                {"role": msg.role, "content": msg.content}
                for msg in request.conversation_history
            ]

        # Execute query through agent
        result = agent.query(
            question=request.query,
            include_sql=request.include_sql,
            include_raw_data=request.include_raw_data,
            conversation_history=conversation_history
        )

        logger.info(
            f"Query completed: success={result.get('success')}, "
            f"time={result.get('execution_time_ms')}ms"
        )

        # Cache successful responses
        if result.get('success'):
            query_cache.set(request.query, result)

        # Record analytics
        analytics.record_query(
            query=request.query,
            response_time_ms=result.get('execution_time_ms', 0),
            success=result.get('success', False),
            error=result.get('error')
        )

        # Return response
        return QueryResponse(**result)

    except Exception as e:
        logger.error(f"Query error: {e}", exc_info=True)

        # Check for rate limit or token limit errors
        error_str = str(e).lower()
        is_rate_limit = any(phrase in error_str for phrase in [
            "rate_limit_error",
            "rate limit",
            "too many requests",
            "quota exceeded"
        ])
        is_token_limit = any(phrase in error_str for phrase in [
            "maximum context length",
            "token limit",
            "context_length_exceeded",
            "too many tokens"
        ])

        # Use custom error message for rate/token limits
        if is_rate_limit or is_token_limit:
            custom_message = (
                "The developer doesn't have enough money to pay for a question this complex. "
                "Please rephrase or ask something simpler."
            )
            return QueryResponse(
                success=False,
                answer=custom_message,
                execution_time_ms=0,
                tool_calls=0,
                turns=0,
                error=custom_message
            )

        # Return generic error response for other errors
        return QueryResponse(
            success=False,
            answer=f"I encountered an error processing your question: {str(e)}",
            execution_time_ms=0,
            tool_calls=0,
            turns=0,
            error=str(e)
        )
