"""Pydantic models for individual holdings."""

from typing import Optional
from pydantic import BaseModel, Field, field_validator


class HoldingRecord(BaseModel):
    """
    Individual position (holding) from a Form 13F filing.

    Represents one row from the information table.
    """

    cusip: str = Field(
        ...,
        description="9-character CUSIP security identifier",
        min_length=9,
        max_length=9
    )
    issuer_name: str = Field(..., description="Company name (e.g., 'APPLE INC')")
    ticker: Optional[str] = Field(
        None,
        description="Stock ticker symbol (e.g., 'AAPL')",
        max_length=10
    )
    title_of_class: str = Field(
        ...,
        description="Type of security (e.g., 'COM' for common stock)"
    )
    value_thousands: int = Field(
        ...,
        description="Market value of position in thousands of dollars",
        ge=0
    )
    shares_or_principal: int = Field(
        ...,
        description="Number of shares (or principal amount for bonds)",
        ge=0
    )
    sh_or_prn: str = Field(
        ...,
        description="'SH' for shares, 'PRN' for principal",
        pattern=r'^(SH|PRN)$'
    )
    investment_discretion: str = Field(
        ...,
        description="Who has discretion: 'SOLE', 'SHARED', or 'DEFINED'",
        pattern=r'^(SOLE|SHARED|DEFINED)$'
    )
    put_call: Optional[str] = Field(
        None,
        description="'PUT' or 'CALL' for options, None otherwise",
        pattern=r'^(PUT|CALL)$'
    )
    voting_authority_sole: int = Field(default=0, description="Shares with sole voting authority", ge=0)
    voting_authority_shared: int = Field(default=0, description="Shares with shared voting authority", ge=0)
    voting_authority_none: int = Field(default=0, description="Shares with no voting authority", ge=0)

    @field_validator('cusip')
    @classmethod
    def validate_cusip(cls, v: str) -> str:
        """Ensure CUSIP is alphanumeric and uppercase."""
        v = v.upper().strip()
        if not v.isalnum():
            raise ValueError('CUSIP must be alphanumeric')
        if len(v) != 9:
            raise ValueError('CUSIP must be exactly 9 characters')
        return v

    @field_validator('ticker')
    @classmethod
    def validate_ticker(cls, v: Optional[str]) -> Optional[str]:
        """Uppercase ticker symbols."""
        return v.upper().strip() if v else None

    @property
    def value_dollars(self) -> int:
        """Value in dollars (not thousands)."""
        return self.value_thousands * 1000

    @property
    def is_option(self) -> bool:
        """Whether this is an options position."""
        return self.put_call is not None

    class Config:
        json_schema_extra = {
            "example": {
                "cusip": "037833100",
                "issuer_name": "APPLE INC",
                "ticker": "AAPL",
                "title_of_class": "COM",
                "value_thousands": 157000000,
                "shares_or_principal": 916000000,
                "sh_or_prn": "SH",
                "investment_discretion": "SOLE",
                "put_call": None,
                "voting_authority_sole": 916000000,
                "voting_authority_shared": 0,
                "voting_authority_none": 0
            }
        }
