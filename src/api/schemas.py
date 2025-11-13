"""
API Request/Response Models (Pydantic Schemas)

Defines data validation and serialization for FastAPI endpoints.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime


# Query Endpoints
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


# Error Response
class ErrorResponse(BaseModel):
    """Standard error response"""

    detail: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(None, description="Error code for client handling")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


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
