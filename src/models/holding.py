"""Pydantic models for individual holdings."""

from typing import Optional
from pydantic import BaseModel, Field, field_validator


class HoldingRecord(BaseModel):
    """
    Individual position (holding) from a Form 13F filing.

    Represents one row from INFOTABLE.tsv.
    """

    accession_number: str = Field(
        ...,
        description="Links to filing in SUBMISSION.tsv",
        max_length=25
    )
    cusip: str = Field(
        ...,
        description="9-character CUSIP security identifier",
        min_length=9,
        max_length=9
    )
    issuer_name: str = Field(
        ...,
        description="Company name (NAMEOFISSUER from TSV)",
        max_length=200
    )
    title_of_class: str = Field(
        ...,
        description="Type of security (e.g., 'COM' for common stock)",
        max_length=150
    )
    value: int = Field(
        ...,
        description="Market value in dollars (not thousands!)",
        ge=0
    )
    shares_or_principal: int = Field(
        ...,
        description="Number of shares or principal amount (SSHPRNAMT)",
        ge=0
    )
    sh_or_prn: str = Field(
        ...,
        description="'SH' for shares, 'PRN' for principal (SSHPRNAMTTYPE)",
        max_length=10
    )
    investment_discretion: str = Field(
        ...,
        description="Who has discretion: 'SOLE', 'SHARED', or 'DEFINED'",
        max_length=10
    )
    put_call: Optional[str] = Field(
        None,
        description="'PUT' or 'CALL' for options, None otherwise (PUTCALL)",
        max_length=10
    )
    voting_authority_sole: int = Field(
        default=0,
        description="Shares with sole voting authority",
        ge=0
    )
    voting_authority_shared: int = Field(
        default=0,
        description="Shares with shared voting authority",
        ge=0
    )
    voting_authority_none: int = Field(
        default=0,
        description="Shares with no voting authority",
        ge=0
    )
    figi: Optional[str] = Field(
        None,
        description="Financial Instrument Global Identifier",
        max_length=12
    )

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

    @property
    def value_millions(self) -> float:
        """Value in millions of dollars."""
        return self.value / 1_000_000

    @property
    def is_option(self) -> bool:
        """Whether this is an options position."""
        return self.put_call is not None

    class Config:
        json_schema_extra = {
            "example": {
                "accession_number": "0001067983-25-000001",
                "cusip": "037833100",
                "issuer_name": "APPLE INC",
                "title_of_class": "COM",
                "value": 157000000000,
                "shares_or_principal": 916000000,
                "sh_or_prn": "SH",
                "investment_discretion": "SOLE",
                "put_call": None,
                "voting_authority_sole": 916000000,
                "voting_authority_shared": 0,
                "voting_authority_none": 0,
                "figi": None
            }
        }
