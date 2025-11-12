"""SQLAlchemy database models for Form 13F data."""

from datetime import date
from sqlalchemy import (
    String,
    Integer,
    BigInteger,
    Date,
    Index,
    ForeignKey,
    CheckConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List

from .base import Base


class Manager(Base):
    """
    Institutional manager (filer) reference table.

    Denormalized from filings for easier querying.
    """
    __tablename__ = "managers"

    cik: Mapped[str] = mapped_column(String(10), primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)

    # Relationships
    filings: Mapped[List["Filing"]] = relationship(
        "Filing",
        back_populates="manager",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Manager(cik={self.cik}, name={self.name})>"


class Issuer(Base):
    """
    Security issuer reference table.

    Denormalized from holdings for easier querying and ticker lookups.
    """
    __tablename__ = "issuers"

    cusip: Mapped[str] = mapped_column(String(9), primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    figi: Mapped[str | None] = mapped_column(String(12), nullable=True, index=True)

    # Relationships
    holdings: Mapped[List["Holding"]] = relationship(
        "Holding",
        back_populates="issuer",
    )

    def __repr__(self) -> str:
        return f"<Issuer(cusip={self.cusip}, name={self.name})>"


class Filing(Base):
    """
    Form 13F filing metadata.

    Contains information about the institutional manager's quarterly filing.
    """
    __tablename__ = "filings"

    # Primary key
    accession_number: Mapped[str] = mapped_column(
        String(25),
        primary_key=True,
        index=True,
    )

    # Foreign keys
    cik: Mapped[str] = mapped_column(
        String(10),
        ForeignKey("managers.cik", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Filing metadata
    filing_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    period_of_report: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    submission_type: Mapped[str] = mapped_column(String(10), nullable=False)
    report_type: Mapped[str] = mapped_column(String(30), nullable=False)

    # Summary statistics
    total_value: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        index=True,
    )
    number_of_holdings: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relationships
    manager: Mapped["Manager"] = relationship(
        "Manager",
        back_populates="filings",
    )
    holdings: Mapped[List["Holding"]] = relationship(
        "Holding",
        back_populates="filing",
        cascade="all, delete-orphan",
    )

    # Constraints
    __table_args__ = (
        CheckConstraint("total_value >= 0", name="check_total_value_positive"),
        CheckConstraint("number_of_holdings >= 0", name="check_holdings_count_positive"),
        Index("ix_filings_cik_period", "cik", "period_of_report"),
        Index("ix_filings_period_value", "period_of_report", "total_value"),
    )

    def __repr__(self) -> str:
        return f"<Filing(accession={self.accession_number}, cik={self.cik}, period={self.period_of_report})>"


class Holding(Base):
    """
    Individual security position from a Form 13F filing.

    Represents one holding (investment) by an institutional manager.
    """
    __tablename__ = "holdings"

    # Primary key (composite: filing + holding sequence)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Foreign keys
    accession_number: Mapped[str] = mapped_column(
        String(25),
        ForeignKey("filings.accession_number", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    cusip: Mapped[str] = mapped_column(
        String(9),
        ForeignKey("issuers.cusip", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Position details
    title_of_class: Mapped[str] = mapped_column(String(150), nullable=False)
    value: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    shares_or_principal: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sh_or_prn: Mapped[str] = mapped_column(String(10), nullable=False)

    # Investment details
    investment_discretion: Mapped[str] = mapped_column(String(10), nullable=False)
    put_call: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # Voting authority
    voting_authority_sole: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    voting_authority_shared: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    voting_authority_none: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)

    # Relationships
    filing: Mapped["Filing"] = relationship(
        "Filing",
        back_populates="holdings",
    )
    issuer: Mapped["Issuer"] = relationship(
        "Issuer",
        back_populates="holdings",
    )

    # Constraints and indexes
    __table_args__ = (
        CheckConstraint("value >= 0", name="check_value_positive"),
        CheckConstraint("shares_or_principal >= 0", name="check_shares_positive"),
        CheckConstraint("voting_authority_sole >= 0", name="check_voting_sole_positive"),
        CheckConstraint("voting_authority_shared >= 0", name="check_voting_shared_positive"),
        CheckConstraint("voting_authority_none >= 0", name="check_voting_none_positive"),
        Index("ix_holdings_accession_cusip", "accession_number", "cusip"),
        Index("ix_holdings_cusip_value", "cusip", "value"),
        Index("ix_holdings_value_desc", "value", postgresql_ops={"value": "DESC"}),
    )

    def __repr__(self) -> str:
        return f"<Holding(id={self.id}, cusip={self.cusip}, value=${self.value:,})>"
