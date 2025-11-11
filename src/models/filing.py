"""Pydantic models for Form 13F filings."""

from datetime import date
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class FilingMetadata(BaseModel):
    """
    Metadata about a Form 13F filing.

    This corresponds to the cover page and summary information.
    """

    accession_number: str = Field(
        ...,
        description="SEC filing identifier (e.g., '0001067983-25-000001')",
        pattern=r'^\d{10}-\d{2}-\d{6}$'
    )
    cik: str = Field(
        ...,
        description="Central Index Key - 10-digit manager identifier",
        pattern=r'^\d{10}$'
    )
    manager_name: str = Field(..., description="Name of institutional manager")
    filing_date: date = Field(..., description="Date filing was submitted to SEC")
    period_of_report: date = Field(..., description="Quarter-end date")
    total_value_thousands: int = Field(
        ...,
        description="Total portfolio value in thousands of dollars",
        ge=0
    )
    number_of_holdings: int = Field(..., description="Count of positions", ge=0)
    raw_xml_url: Optional[str] = None

    @field_validator('cik')
    @classmethod
    def pad_cik(cls, v: str) -> str:
        """Ensure CIK is zero-padded to 10 digits."""
        return v.zfill(10)

    class Config:
        json_schema_extra = {
            "example": {
                "accession_number": "0001067983-25-000001",
                "cik": "0001067983",
                "manager_name": "BERKSHIRE HATHAWAY INC",
                "filing_date": "2025-02-14",
                "period_of_report": "2024-12-31",
                "total_value_thousands": 390500000,
                "number_of_holdings": 45
            }
        }


class ParsedFiling(BaseModel):
    """
    Complete parsed Form 13F filing.

    Contains metadata, holdings, and optionally commentary text.
    """

    metadata: FilingMetadata
    holdings: List["HoldingRecord"]
    commentary_text: Optional[str] = None  # For Phase 7 (RAG)
    raw_xml: Optional[str] = None  # Store for audit trail

    @property
    def num_holdings(self) -> int:
        """Number of holdings in this filing."""
        return len(self.holdings)

    class Config:
        json_schema_extra = {
            "example": {
                "metadata": {
                    "accession_number": "0001067983-25-000001",
                    "cik": "0001067983",
                    "manager_name": "BERKSHIRE HATHAWAY INC",
                    "filing_date": "2025-02-14",
                    "period_of_report": "2024-12-31",
                    "total_value_thousands": 390500000,
                    "number_of_holdings": 45
                },
                "holdings": [],
                "commentary_text": None
            }
        }


# Forward reference resolution
from .holding import HoldingRecord
ParsedFiling.model_rebuild()
