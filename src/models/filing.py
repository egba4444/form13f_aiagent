"""Pydantic models for Form 13F filings."""

from datetime import date
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class FilingMetadata(BaseModel):
    """
    Metadata about a Form 13F filing.

    Combined from SUBMISSION.tsv, COVERPAGE.tsv, and SUMMARYPAGE.tsv.
    """

    accession_number: str = Field(
        ...,
        description="SEC filing identifier (e.g., '0001067983-25-000001')",
        max_length=25
    )
    cik: str = Field(
        ...,
        description="Central Index Key - manager identifier",
        max_length=10
    )
    filing_date: date = Field(..., description="Date filing was submitted to SEC")
    period_of_report: date = Field(..., description="Quarter-end date")
    submission_type: str = Field(
        ...,
        description="13F-HR (holdings report), 13F-NT (notice), or amendment",
        max_length=10
    )

    # From COVERPAGE.tsv
    manager_name: str = Field(..., description="Name of institutional manager", max_length=150)
    report_type: str = Field(
        ...,
        description="Report type: 13F holdings report, 13F notice, or 13F combination report",
        max_length=30
    )

    # From SUMMARYPAGE.tsv
    total_value: int = Field(
        ...,
        description="Total portfolio value in dollars (not thousands!)",
        ge=0
    )
    number_of_holdings: int = Field(
        ...,
        description="Count of positions (table entry total)",
        ge=0
    )

    @field_validator('cik')
    @classmethod
    def pad_cik(cls, v: str) -> str:
        """Ensure CIK is zero-padded to 10 digits."""
        return v.zfill(10)

    @property
    def total_value_millions(self) -> float:
        """Total portfolio value in millions of dollars."""
        return self.total_value / 1_000_000

    class Config:
        json_schema_extra = {
            "example": {
                "accession_number": "0001067983-25-000001",
                "cik": "0001067983",
                "filing_date": "2025-02-14",
                "period_of_report": "2024-12-31",
                "submission_type": "13F-HR",
                "manager_name": "BERKSHIRE HATHAWAY INC",
                "report_type": "13F HOLDINGS REPORT",
                "total_value": 390500000000,
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
