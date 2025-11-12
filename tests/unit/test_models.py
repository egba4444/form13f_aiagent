"""Unit tests for Pydantic data models."""

import pytest
from datetime import date
from pydantic import ValidationError

from src.models.filing import FilingMetadata, ParsedFiling
from src.models.holding import HoldingRecord


class TestFilingMetadata:
    """Tests for FilingMetadata model."""

    def test_valid_filing_metadata(self):
        """Test creating a valid FilingMetadata object."""
        filing = FilingMetadata(
            accession_number="0001234567-25-000001",
            cik="1234567",
            filing_date=date(2025, 2, 14),
            period_of_report=date(2024, 12, 31),
            submission_type="13F-HR",
            manager_name="TEST CAPITAL MANAGEMENT LLC",
            report_type="13F HOLDINGS REPORT",
            total_value=500000000,
            number_of_holdings=3,
        )

        assert filing.accession_number == "0001234567-25-000001"
        assert filing.cik == "0001234567"  # Should be zero-padded
        assert filing.filing_date == date(2025, 2, 14)
        assert filing.period_of_report == date(2024, 12, 31)
        assert filing.submission_type == "13F-HR"
        assert filing.manager_name == "TEST CAPITAL MANAGEMENT LLC"
        assert filing.total_value == 500000000
        assert filing.number_of_holdings == 3

    def test_cik_zero_padding(self):
        """Test that CIK gets zero-padded to 10 digits."""
        filing = FilingMetadata(
            accession_number="0001234567-25-000001",
            cik="123",
            filing_date=date(2025, 2, 14),
            period_of_report=date(2024, 12, 31),
            submission_type="13F-HR",
            manager_name="TEST MANAGER",
            report_type="13F HOLDINGS REPORT",
            total_value=1000000,
            number_of_holdings=1,
        )

        assert filing.cik == "0000000123"

    def test_total_value_millions_property(self):
        """Test total_value_millions property."""
        filing = FilingMetadata(
            accession_number="0001234567-25-000001",
            cik="1234567",
            filing_date=date(2025, 2, 14),
            period_of_report=date(2024, 12, 31),
            submission_type="13F-HR",
            manager_name="TEST MANAGER",
            report_type="13F HOLDINGS REPORT",
            total_value=1500000000,  # $1.5B
            number_of_holdings=1,
        )

        assert filing.total_value_millions == 1500.0

    def test_negative_total_value_fails(self):
        """Test that negative total_value raises validation error."""
        with pytest.raises(ValidationError):
            FilingMetadata(
                accession_number="0001234567-25-000001",
                cik="1234567",
                filing_date=date(2025, 2, 14),
                period_of_report=date(2024, 12, 31),
                submission_type="13F-HR",
                manager_name="TEST MANAGER",
                report_type="13F HOLDINGS REPORT",
                total_value=-1000000,  # Negative value
                number_of_holdings=1,
            )

    def test_negative_number_of_holdings_fails(self):
        """Test that negative number_of_holdings raises validation error."""
        with pytest.raises(ValidationError):
            FilingMetadata(
                accession_number="0001234567-25-000001",
                cik="1234567",
                filing_date=date(2025, 2, 14),
                period_of_report=date(2024, 12, 31),
                submission_type="13F-HR",
                manager_name="TEST MANAGER",
                report_type="13F HOLDINGS REPORT",
                total_value=1000000,
                number_of_holdings=-5,  # Negative count
            )


class TestHoldingRecord:
    """Tests for HoldingRecord model."""

    def test_valid_holding_record(self):
        """Test creating a valid HoldingRecord object."""
        holding = HoldingRecord(
            accession_number="0001234567-25-000001",
            cusip="037833100",
            issuer_name="APPLE INC",
            title_of_class="COM",
            value=200000000,
            shares_or_principal=500000,
            sh_or_prn="SH",
            investment_discretion="SOLE",
            put_call=None,
            voting_authority_sole=500000,
            voting_authority_shared=0,
            voting_authority_none=0,
            figi="BBG000B9XRY4",
        )

        assert holding.accession_number == "0001234567-25-000001"
        assert holding.cusip == "037833100"
        assert holding.issuer_name == "APPLE INC"
        assert holding.value == 200000000
        assert holding.shares_or_principal == 500000
        assert holding.sh_or_prn == "SH"
        assert holding.investment_discretion == "SOLE"
        assert holding.put_call is None
        assert not holding.is_option

    def test_cusip_validation_uppercase(self):
        """Test that CUSIP is converted to uppercase."""
        holding = HoldingRecord(
            accession_number="0001234567-25-000001",
            cusip="037833100",  # Lowercase
            issuer_name="APPLE INC",
            title_of_class="COM",
            value=200000000,
            shares_or_principal=500000,
            sh_or_prn="SH",
            investment_discretion="SOLE",
        )

        assert holding.cusip == "037833100"

    def test_cusip_wrong_length_fails(self):
        """Test that CUSIP with wrong length fails validation."""
        with pytest.raises(ValidationError):
            HoldingRecord(
                accession_number="0001234567-25-000001",
                cusip="12345",  # Too short
                issuer_name="TEST COMPANY",
                title_of_class="COM",
                value=1000000,
                shares_or_principal=1000,
                sh_or_prn="SH",
                investment_discretion="SOLE",
            )

    def test_value_millions_property(self):
        """Test value_millions property."""
        holding = HoldingRecord(
            accession_number="0001234567-25-000001",
            cusip="037833100",
            issuer_name="APPLE INC",
            title_of_class="COM",
            value=250000000,  # $250M
            shares_or_principal=500000,
            sh_or_prn="SH",
            investment_discretion="SOLE",
        )

        assert holding.value_millions == 250.0

    def test_is_option_with_put(self):
        """Test is_option property with PUT option."""
        holding = HoldingRecord(
            accession_number="0001234567-25-000001",
            cusip="037833100",
            issuer_name="APPLE INC",
            title_of_class="PUT",
            value=5000000,
            shares_or_principal=100,
            sh_or_prn="SH",
            investment_discretion="SOLE",
            put_call="PUT",
        )

        assert holding.is_option

    def test_is_option_with_call(self):
        """Test is_option property with CALL option."""
        holding = HoldingRecord(
            accession_number="0001234567-25-000001",
            cusip="037833100",
            issuer_name="APPLE INC",
            title_of_class="CALL",
            value=5000000,
            shares_or_principal=100,
            sh_or_prn="SH",
            investment_discretion="SOLE",
            put_call="CALL",
        )

        assert holding.is_option

    def test_negative_value_fails(self):
        """Test that negative value raises validation error."""
        with pytest.raises(ValidationError):
            HoldingRecord(
                accession_number="0001234567-25-000001",
                cusip="037833100",
                issuer_name="TEST COMPANY",
                title_of_class="COM",
                value=-1000000,  # Negative value
                shares_or_principal=1000,
                sh_or_prn="SH",
                investment_discretion="SOLE",
            )

    def test_negative_shares_fails(self):
        """Test that negative shares raises validation error."""
        with pytest.raises(ValidationError):
            HoldingRecord(
                accession_number="0001234567-25-000001",
                cusip="037833100",
                issuer_name="TEST COMPANY",
                title_of_class="COM",
                value=1000000,
                shares_or_principal=-1000,  # Negative shares
                sh_or_prn="SH",
                investment_discretion="SOLE",
            )


class TestParsedFiling:
    """Tests for ParsedFiling model."""

    def test_valid_parsed_filing(self):
        """Test creating a valid ParsedFiling object."""
        metadata = FilingMetadata(
            accession_number="0001234567-25-000001",
            cik="1234567",
            filing_date=date(2025, 2, 14),
            period_of_report=date(2024, 12, 31),
            submission_type="13F-HR",
            manager_name="TEST CAPITAL MANAGEMENT LLC",
            report_type="13F HOLDINGS REPORT",
            total_value=500000000,
            number_of_holdings=2,
        )

        holdings = [
            HoldingRecord(
                accession_number="0001234567-25-000001",
                cusip="037833100",
                issuer_name="APPLE INC",
                title_of_class="COM",
                value=300000000,
                shares_or_principal=500000,
                sh_or_prn="SH",
                investment_discretion="SOLE",
            ),
            HoldingRecord(
                accession_number="0001234567-25-000001",
                cusip="594918104",
                issuer_name="MICROSOFT CORP",
                title_of_class="COM",
                value=200000000,
                shares_or_principal=300000,
                sh_or_prn="SH",
                investment_discretion="SOLE",
            ),
        ]

        parsed_filing = ParsedFiling(metadata=metadata, holdings=holdings)

        assert parsed_filing.metadata.accession_number == "0001234567-25-000001"
        assert len(parsed_filing.holdings) == 2
        assert parsed_filing.num_holdings == 2

    def test_parsed_filing_with_no_holdings(self):
        """Test ParsedFiling with empty holdings list."""
        metadata = FilingMetadata(
            accession_number="0001234567-25-000001",
            cik="1234567",
            filing_date=date(2025, 2, 14),
            period_of_report=date(2024, 12, 31),
            submission_type="13F-HR",
            manager_name="TEST MANAGER",
            report_type="13F HOLDINGS REPORT",
            total_value=0,
            number_of_holdings=0,
        )

        parsed_filing = ParsedFiling(metadata=metadata, holdings=[])

        assert parsed_filing.num_holdings == 0
        assert len(parsed_filing.holdings) == 0
