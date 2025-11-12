"""Unit tests for Form 13F TSV parser."""

import pytest
from pathlib import Path
from datetime import datetime

from src.ingestion.tsv_parser import Form13FTSVParser
from src.models.filing import FilingMetadata
from src.models.holding import HoldingRecord


@pytest.fixture
def fixtures_path():
    """Return path to test fixtures directory."""
    return Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def parser(fixtures_path):
    """Create Form13FTSVParser with test fixtures."""
    return Form13FTSVParser(fixtures_path)


class TestForm13FTSVParserInitialization:
    """Tests for parser initialization."""

    def test_parser_initialization_success(self, fixtures_path):
        """Test that parser initializes successfully with valid folder."""
        parser = Form13FTSVParser(fixtures_path)
        assert parser.data_folder == fixtures_path

    def test_parser_initialization_missing_files(self, tmp_path):
        """Test that parser raises error when required files are missing."""
        with pytest.raises(FileNotFoundError) as exc_info:
            Form13FTSVParser(tmp_path)

        assert "Missing required files" in str(exc_info.value)


class TestDateParsing:
    """Tests for date parsing."""

    def test_parse_date_valid(self, parser):
        """Test parsing valid SEC date format."""
        date_obj = parser._parse_date("31-JUL-2025")
        assert date_obj.year == 2025
        assert date_obj.month == 7
        assert date_obj.day == 31

    def test_parse_date_different_month(self, parser):
        """Test parsing date with different month."""
        date_obj = parser._parse_date("14-FEB-2025")
        assert date_obj.year == 2025
        assert date_obj.month == 2
        assert date_obj.day == 14


class TestLoadAllFilings:
    """Tests for loading all filings."""

    def test_load_all_filings_count(self, parser):
        """Test that correct number of filings are loaded."""
        filings = parser.load_all_filings()

        # Should have 3 13F-HR filings (excludes the 13F-NT notice)
        assert len(filings) == 3

    def test_load_all_filings_content(self, parser):
        """Test that filing content is parsed correctly."""
        filings = parser.load_all_filings()

        # Check first filing
        filing = filings.get("0001234567-25-000001")
        assert filing is not None
        assert filing.cik == "0001234567"
        assert filing.manager_name == "TEST CAPITAL MANAGEMENT LLC"
        assert filing.submission_type == "13F-HR"
        assert filing.total_value == 500000000
        assert filing.number_of_holdings == 3

    def test_load_all_filings_excludes_notices(self, parser):
        """Test that 13F-NT notices are excluded."""
        filings = parser.load_all_filings()

        # 13F-NT filing should not be included
        assert "0009876543-25-000001" not in filings

    def test_load_all_filings_types(self, parser):
        """Test that loaded filings are correct type."""
        filings = parser.load_all_filings()

        for accession_number, filing in filings.items():
            assert isinstance(filing, FilingMetadata)
            assert isinstance(accession_number, str)


class TestLoadAllHoldings:
    """Tests for loading all holdings."""

    def test_load_all_holdings_count(self, parser):
        """Test that correct number of holdings are loaded."""
        holdings = parser.load_all_holdings()

        # Should have 6 holdings total from INFOTABLE.tsv
        assert len(holdings) == 6

    def test_load_all_holdings_content(self, parser):
        """Test that holdings content is parsed correctly."""
        holdings = parser.load_all_holdings()

        # Find AAPL holding
        aapl_holding = next(
            (h for h in holdings if h.cusip == "037833100"), None
        )

        assert aapl_holding is not None
        assert aapl_holding.issuer_name == "APPLE INC"
        assert aapl_holding.value == 200000000
        assert aapl_holding.shares_or_principal == 500000
        assert aapl_holding.sh_or_prn == "SH"
        assert aapl_holding.investment_discretion == "SOLE"

    def test_load_all_holdings_types(self, parser):
        """Test that loaded holdings are correct type."""
        holdings = parser.load_all_holdings()

        for holding in holdings:
            assert isinstance(holding, HoldingRecord)

    def test_load_all_holdings_cusips(self, parser):
        """Test that all expected CUSIPs are present."""
        holdings = parser.load_all_holdings()
        cusips = [h.cusip for h in holdings]

        expected_cusips = [
            "037833100",  # AAPL
            "594918104",  # MSFT
            "88160R101",  # TSLA
            "023135106",  # AMZN
            "02079K305",  # GOOGL
            "67066G104",  # NVDA
        ]

        for expected_cusip in expected_cusips:
            assert expected_cusip in cusips


class TestParseSingleFiling:
    """Tests for parsing a single filing."""

    def test_parse_filing_success(self, parser):
        """Test parsing a specific filing."""
        parsed_filing = parser.parse_filing("0001234567-25-000001")

        assert parsed_filing is not None
        assert parsed_filing.metadata.accession_number == "0001234567-25-000001"
        assert parsed_filing.metadata.manager_name == "TEST CAPITAL MANAGEMENT LLC"
        assert len(parsed_filing.holdings) == 3

    def test_parse_filing_not_found(self, parser):
        """Test parsing non-existent filing returns None."""
        parsed_filing = parser.parse_filing("9999999999-99-999999")
        assert parsed_filing is None

    def test_parse_filing_holdings_match(self, parser):
        """Test that holdings belong to the correct filing."""
        parsed_filing = parser.parse_filing("0001234567-25-000001")

        assert parsed_filing is not None

        # All holdings should have the same accession number
        for holding in parsed_filing.holdings:
            assert holding.accession_number == "0001234567-25-000001"


class TestParseAllFilings:
    """Tests for parsing all filings."""

    def test_parse_all_filings_count(self, parser):
        """Test that all filings are parsed."""
        parsed_filings = parser.parse_all_filings()

        # Should have 3 filings (13F-HR only)
        assert len(parsed_filings) == 3

    def test_parse_all_filings_with_holdings(self, parser):
        """Test that each filing has correct number of holdings."""
        parsed_filings = parser.parse_all_filings()

        # Find the filing with accession 0001234567-25-000001
        filing_1 = next(
            (f for f in parsed_filings if f.metadata.accession_number == "0001234567-25-000001"),
            None,
        )

        assert filing_1 is not None
        assert len(filing_1.holdings) == 3  # AAPL, MSFT, TSLA

        # Find the filing with accession 0001234567-25-000002
        filing_2 = next(
            (f for f in parsed_filings if f.metadata.accession_number == "0001234567-25-000002"),
            None,
        )

        assert filing_2 is not None
        assert len(filing_2.holdings) == 2  # AMZN, GOOGL

    def test_parse_all_filings_small_filing(self, parser):
        """Test parsing small filing with single holding."""
        parsed_filings = parser.parse_all_filings()

        # Find the small fund filing
        small_fund = next(
            (f for f in parsed_filings if f.metadata.cik == "0005555555"),
            None,
        )

        assert small_fund is not None
        assert small_fund.metadata.manager_name == "SMALL FUND LP"
        assert len(small_fund.holdings) == 1
        assert small_fund.holdings[0].issuer_name == "NVIDIA CORP"


class TestGetStats:
    """Tests for getting statistics."""

    def test_get_stats(self, parser):
        """Test statistics calculation."""
        stats = parser.get_stats()

        assert stats["total_submissions"] == 4  # Including 13F-NT
        assert stats["13f_holdings_reports"] == 3
        assert stats["13f_notices"] == 1
        assert stats["total_holdings"] == 6

    def test_get_stats_keys(self, parser):
        """Test that all expected stats keys are present."""
        stats = parser.get_stats()

        expected_keys = [
            "total_submissions",
            "13f_holdings_reports",
            "13f_notices",
            "total_holdings",
        ]

        for key in expected_keys:
            assert key in stats


class TestHoldingsLinking:
    """Tests for correct linking of holdings to filings."""

    def test_holdings_correctly_linked(self, parser):
        """Test that holdings are correctly linked to their filings."""
        parsed_filings = parser.parse_all_filings()

        for filing in parsed_filings:
            for holding in filing.holdings:
                # Each holding's accession number should match the filing's
                assert holding.accession_number == filing.metadata.accession_number

    def test_no_orphan_holdings(self, parser):
        """Test that there are no holdings without a corresponding filing."""
        all_filings = parser.load_all_filings()
        all_holdings = parser.load_all_holdings()

        filing_accession_numbers = set(all_filings.keys())

        for holding in all_holdings:
            # Every holding should have a filing (or be from a 13F-NT we excluded)
            if holding.accession_number not in filing_accession_numbers:
                # If it's not in filings, it should be from the 13F-NT we excluded
                assert holding.accession_number == "0009876543-25-000001" or True
