"""
API Request/Response Models (Pydantic Schemas)

Defines data validation and serialization for FastAPI endpoints.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime


# Query Endpoints
class ConversationMessage(BaseModel):
    """Single message in conversation history"""

    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")


class QueryRequest(BaseModel):
    """Request model for natural language query"""

    query: str = Field(
        ...,
        min_length=3,
        max_length=500,
        description="Natural language question about Form 13F data",
        examples=["How many Apple shares did Berkshire Hathaway hold in Q4 2024?"]
    )
    include_sql: bool = Field(
        default=False,
        description="Include generated SQL query in response"
    )
    include_raw_data: bool = Field(
        default=False,
        description="Include raw query results in response"
    )
    conversation_history: Optional[List[ConversationMessage]] = Field(
        default=None,
        description="Previous conversation messages for context"
    )


class QueryResponse(BaseModel):
    """Response model for natural language query"""

    success: bool = Field(..., description="Whether query succeeded")
    answer: str = Field(..., description="Natural language answer")
    sql_query: Optional[str] = Field(None, description="Generated SQL query (if requested)")
    all_sql_queries: Optional[List[str]] = Field(None, description="All SQL queries executed")
    raw_data: Optional[List[Dict[str, Any]]] = Field(None, description="Raw query results (if requested)")
    execution_time_ms: int = Field(..., description="Total execution time in milliseconds")
    tool_calls: int = Field(..., description="Number of tool calls made")
    turns: int = Field(..., description="Conversation turns taken")
    error: Optional[str] = Field(None, description="Error message if failed")


# Health Check
class HealthResponse(BaseModel):
    """Health check response"""

    status: str = Field(..., description="Service status", examples=["healthy"])
    database: str = Field(..., description="Database connection status", examples=["connected"])
    llm: str = Field(..., description="LLM provider status", examples=["configured"])
    version: str = Field(..., description="API version", examples=["0.1.0"])
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Current server time")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# Error Response
class ErrorResponse(BaseModel):
    """Standard error response"""

    detail: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(None, description="Error code for client handling")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# Manager Models
class ManagerResponse(BaseModel):
    """Manager information"""

    cik: str = Field(..., description="Central Index Key (10 digits)")
    name: str = Field(..., description="Manager name")

    class Config:
        from_attributes = True


class ManagerListResponse(BaseModel):
    """List of managers with pagination"""

    managers: List[ManagerResponse]
    total: int = Field(..., description="Total number of managers")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Items per page")


# Filing Models
class FilingResponse(BaseModel):
    """Filing information"""

    accession_number: str = Field(..., description="SEC accession number")
    cik: str = Field(..., description="Manager CIK")
    filing_date: str = Field(..., description="Date filed with SEC")
    period_of_report: str = Field(..., description="Quarter end date")
    submission_type: str = Field(..., description="Submission type")
    report_type: str = Field(..., description="Report type")
    total_value: int = Field(..., description="Total portfolio value in USD")
    number_of_holdings: int = Field(..., description="Number of positions")

    class Config:
        from_attributes = True


class FilingListResponse(BaseModel):
    """List of filings with pagination"""

    filings: List[FilingResponse]
    total: int
    page: int
    page_size: int


# Holding Models
class HoldingResponse(BaseModel):
    """Individual holding/position"""

    id: int
    accession_number: str
    cusip: str = Field(..., description="9-character CUSIP")
    title_of_class: str = Field(..., description="Security name/title")
    value: int = Field(..., description="Position value in USD")
    shares_or_principal: int = Field(..., description="Number of shares")
    sh_or_prn: str = Field(..., description="SH (shares) or PRN (principal)")
    investment_discretion: str = Field(..., description="SOLE, SHARED, or DFND")
    put_call: Optional[str] = Field(None, description="PUT, CALL, or None")
    voting_authority_sole: int
    voting_authority_shared: int
    voting_authority_none: int

    class Config:
        from_attributes = True


class HoldingListResponse(BaseModel):
    """List of holdings with pagination"""

    holdings: List[HoldingResponse]
    total: int
    page: int
    page_size: int


# Statistics
class DatabaseStatsResponse(BaseModel):
    """Database statistics"""

    managers_count: int
    issuers_count: int
    filings_count: int
    holdings_count: int
    latest_quarter: Optional[str] = None
    total_value: Optional[int] = Field(None, description="Total value across all holdings")


# Analytics Models
class PortfolioHolding(BaseModel):
    """Individual holding in a portfolio"""
    cusip: str
    title_of_class: str
    value: int
    shares_or_principal: int
    percent_of_portfolio: float = Field(..., description="Percentage of total portfolio value")


class PortfolioCompositionResponse(BaseModel):
    """Portfolio composition analysis for a manager"""
    cik: str
    manager_name: str
    period: str
    total_value: int
    number_of_holdings: int
    top_holdings: List[PortfolioHolding] = Field(..., description="Top holdings by value")
    concentration: Dict[str, float] = Field(
        ...,
        description="Concentration metrics (e.g., top5_percent, top10_percent)"
    )


class PositionChange(BaseModel):
    """Position change over time"""
    cusip: str
    title_of_class: str
    previous_shares: Optional[int]
    current_shares: int
    shares_change: Optional[int]
    shares_change_percent: Optional[float]
    previous_value: Optional[int]
    current_value: int
    value_change: Optional[int]
    value_change_percent: Optional[float]


class PositionHistoryResponse(BaseModel):
    """Historical position changes for a manager"""
    cik: str
    manager_name: str
    cusip: Optional[str] = None
    security_name: Optional[str] = None
    periods: List[str] = Field(..., description="Reporting periods")
    changes: List[PositionChange] = Field(..., description="Position changes over time")


class TopMover(BaseModel):
    """Top position change"""
    cik: str
    manager_name: str
    cusip: str
    title_of_class: str
    previous_value: int
    current_value: int
    value_change: int
    value_change_percent: float
    previous_shares: int
    current_shares: int
    shares_change: int
    shares_change_percent: float


class TopMoversResponse(BaseModel):
    """Top position changes across all managers"""
    period_from: str
    period_to: str
    biggest_increases: List[TopMover]
    biggest_decreases: List[TopMover]
    new_positions: List[Dict[str, Any]] = Field(..., description="Newly established positions")
    closed_positions: List[Dict[str, Any]] = Field(..., description="Completely closed positions")


class SecurityOwnership(BaseModel):
    """Ownership details for a security"""
    cik: str
    manager_name: str
    shares: int
    value: int
    percent_of_total: float = Field(..., description="Percentage of total institutional ownership")


class SecurityAnalysisResponse(BaseModel):
    """Ownership analysis for a specific security"""
    cusip: str
    title_of_class: str
    period: str
    total_institutional_shares: int
    total_institutional_value: int
    number_of_holders: int
    top_holders: List[SecurityOwnership]
    concentration: Dict[str, float] = Field(
        ...,
        description="Ownership concentration metrics"
    )


# ============================================================================
# Watchlist Models
# ============================================================================

class WatchlistItemCreate(BaseModel):
    """Request to add item to watchlist"""

    item_type: str = Field(..., description="Type: 'manager' or 'security'")
    cik: Optional[str] = Field(None, description="Manager CIK (if type=manager)")
    cusip: Optional[str] = Field(None, description="Security CUSIP (if type=security)")
    notes: Optional[str] = Field(None, description="Optional notes about this item")


class WatchlistItemUpdate(BaseModel):
    """Request to update watchlist item"""

    notes: Optional[str] = Field(None, description="Update notes")


class WatchlistItemResponse(BaseModel):
    """Watchlist item with details"""

    id: int = Field(..., description="Item ID")
    item_type: str = Field(..., description="Type: 'manager' or 'security'")
    cik: Optional[str] = Field(None, description="Manager CIK")
    cusip: Optional[str] = Field(None, description="Security CUSIP")
    name: Optional[str] = Field(None, description="Manager or security name")
    notes: Optional[str] = Field(None, description="User notes")
    added_at: datetime = Field(..., description="When item was added")

    # Metrics (optional, depends on item type)
    latest_value: Optional[int] = Field(None, description="Latest portfolio/holding value")
    value_change_percent: Optional[float] = Field(None, description="Period-over-period change %")
    latest_period: Optional[str] = Field(None, description="Latest reporting period")

    class Config:
        from_attributes = True


class WatchlistResponse(BaseModel):
    """User's watchlist with all items"""

    id: int = Field(..., description="Watchlist ID")
    name: str = Field(..., description="Watchlist name")
    user_id: str = Field(..., description="User ID (UUID)")
    created_at: datetime = Field(..., description="When watchlist was created")
    updated_at: datetime = Field(..., description="Last update time")
    items: List[WatchlistItemResponse] = Field(..., description="Watchlist items")

    class Config:
        from_attributes = True


# ============================================================================
# RAG / Semantic Search Models
# ============================================================================

class SemanticSearchRequest(BaseModel):
    """Request for semantic search over filing text"""

    query: str = Field(
        ...,
        min_length=3,
        max_length=500,
        description="Search query (semantic, not keyword-based)",
        examples=["What investment strategies are mentioned?"]
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of results to return (1-20)"
    )
    filter_accession: Optional[str] = Field(
        None,
        description="Filter to specific filing accession number"
    )
    filter_content_type: Optional[str] = Field(
        None,
        description="Filter to specific content type (e.g., 'explanatory_notes', 'cover_page')"
    )


class SemanticSearchResult(BaseModel):
    """Individual search result"""

    text: str = Field(..., description="Matched text content")
    accession_number: str = Field(..., description="Filing accession number")
    content_type: str = Field(..., description="Section type (e.g., 'explanatory_notes')")
    relevance_score: float = Field(..., description="Relevance score (0.0-1.0)")


class SemanticSearchResponse(BaseModel):
    """Response from semantic search"""

    success: bool = Field(..., description="Whether search succeeded")
    results: List[SemanticSearchResult] = Field(..., description="Search results")
    results_count: int = Field(..., description="Number of results returned")
    query: str = Field(..., description="Original query")


class FilingTextResponse(BaseModel):
    """Text content for a specific filing"""

    success: bool = Field(..., description="Whether retrieval succeeded")
    accession_number: str = Field(..., description="Filing accession number")
    sections: Dict[str, str] = Field(
        ...,
        description="Text sections keyed by content type"
    )
    sections_found: List[str] = Field(
        ...,
        description="List of available content types in this filing"
    )
    total_sections: int = Field(..., description="Number of sections found")
