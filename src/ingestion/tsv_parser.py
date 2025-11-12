"""Parser for Form 13F TSV bulk data files from SEC."""

import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from ..models.filing import FilingMetadata, ParsedFiling
from ..models.holding import HoldingRecord


class Form13FTSVParser:
    """
    Parser for Form 13F TSV files from SEC bulk data.

    Parses SUBMISSION.tsv, COVERPAGE.tsv, SUMMARYPAGE.tsv, and INFOTABLE.tsv
    to create FilingMetadata and HoldingRecord objects.
    """

    def __init__(self, data_folder: Path):
        """
        Initialize parser with path to folder containing TSV files.

        Args:
            data_folder: Path to folder with SUBMISSION.tsv, COVERPAGE.tsv, etc.
        """
        self.data_folder = Path(data_folder)
        self._validate_folder()

    def _validate_folder(self) -> None:
        """Ensure required TSV files exist."""
        required_files = [
            "SUBMISSION.tsv",
            "COVERPAGE.tsv",
            "SUMMARYPAGE.tsv",
            "INFOTABLE.tsv",
        ]

        missing = []
        for filename in required_files:
            if not (self.data_folder / filename).exists():
                missing.append(filename)

        if missing:
            raise FileNotFoundError(
                f"Missing required files in {self.data_folder}: {', '.join(missing)}"
            )

    def _parse_date(self, date_str: str) -> datetime:
        """Parse SEC date format: DD-MON-YYYY (e.g., '31-JUL-2025')."""
        return datetime.strptime(date_str, "%d-%b-%Y")

    def _read_tsv(self, filename: str) -> List[Dict[str, str]]:
        """
        Read TSV file and return list of row dictionaries.

        Args:
            filename: Name of TSV file (e.g., 'SUBMISSION.tsv')

        Returns:
            List of dictionaries, one per row
        """
        file_path = self.data_folder / filename
        rows = []

        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter='\t')
            for row in reader:
                rows.append(row)

        return rows

    def load_all_filings(self) -> Dict[str, FilingMetadata]:
        """
        Load all filings from SUBMISSION, COVERPAGE, and SUMMARYPAGE.

        Returns:
            Dictionary mapping accession_number -> FilingMetadata
        """
        # Load all three TSV files
        submissions = {row['ACCESSION_NUMBER']: row for row in self._read_tsv('SUBMISSION.tsv')}
        coverpages = {row['ACCESSION_NUMBER']: row for row in self._read_tsv('COVERPAGE.tsv')}
        summaries = {row['ACCESSION_NUMBER']: row for row in self._read_tsv('SUMMARYPAGE.tsv')}

        filings = {}

        for accession_number, sub in submissions.items():
            # Only process 13F-HR (holdings reports), skip 13F-NT (notices)
            if sub['SUBMISSIONTYPE'] != '13F-HR':
                continue

            # Get corresponding coverpage and summary (may not exist for all submissions)
            cover = coverpages.get(accession_number)
            summary = summaries.get(accession_number)

            if not cover or not summary:
                # Skip if missing coverpage or summary
                continue

            try:
                filing = FilingMetadata(
                    accession_number=accession_number,
                    cik=sub['CIK'],
                    filing_date=self._parse_date(sub['FILING_DATE']).date(),
                    period_of_report=self._parse_date(sub['PERIODOFREPORT']).date(),
                    submission_type=sub['SUBMISSIONTYPE'],
                    manager_name=cover['FILINGMANAGER_NAME'],
                    report_type=cover['REPORTTYPE'],
                    total_value=int(summary['TABLEVALUETOTAL']) if summary['TABLEVALUETOTAL'] else 0,
                    number_of_holdings=int(summary['TABLEENTRYTOTAL']) if summary['TABLEENTRYTOTAL'] else 0,
                )

                filings[accession_number] = filing
            except (KeyError, ValueError) as e:
                # Skip malformed rows
                print(f"Warning: Skipping filing {accession_number}: {e}")
                continue

        return filings

    def load_all_holdings(self) -> List[HoldingRecord]:
        """
        Load all holdings from INFOTABLE.tsv.

        Returns:
            List of HoldingRecord objects
        """
        holdings = []

        for row in self._read_tsv('INFOTABLE.tsv'):
            try:
                holding = HoldingRecord(
                    accession_number=row['ACCESSION_NUMBER'],
                    cusip=row['CUSIP'],
                    issuer_name=row['NAMEOFISSUER'],
                    title_of_class=row['TITLEOFCLASS'],
                    value=int(row['VALUE']) if row['VALUE'] else 0,
                    shares_or_principal=int(row['SSHPRNAMT']) if row['SSHPRNAMT'] else 0,
                    sh_or_prn=row['SSHPRNAMTTYPE'],
                    investment_discretion=row['INVESTMENTDISCRETION'],
                    put_call=row['PUTCALL'] if row['PUTCALL'] else None,
                    voting_authority_sole=int(row['VOTING_AUTH_SOLE']) if row['VOTING_AUTH_SOLE'] else 0,
                    voting_authority_shared=int(row['VOTING_AUTH_SHARED']) if row['VOTING_AUTH_SHARED'] else 0,
                    voting_authority_none=int(row['VOTING_AUTH_NONE']) if row['VOTING_AUTH_NONE'] else 0,
                    figi=row['FIGI'] if row['FIGI'] else None,
                )

                holdings.append(holding)
            except (KeyError, ValueError) as e:
                # Skip malformed rows
                print(f"Warning: Skipping holding in {row.get('ACCESSION_NUMBER', 'unknown')}: {e}")
                continue

        return holdings

    def parse_filing(self, accession_number: str) -> Optional[ParsedFiling]:
        """
        Parse a single filing with its holdings.

        Args:
            accession_number: Accession number of filing to parse

        Returns:
            ParsedFiling object or None if not found
        """
        # Load all filings and find the requested one
        all_filings = self.load_all_filings()
        metadata = all_filings.get(accession_number)

        if not metadata:
            return None

        # Load holdings for this filing
        all_holdings = self.load_all_holdings()
        filing_holdings = [
            h for h in all_holdings
            if h.accession_number == accession_number
        ]

        return ParsedFiling(
            metadata=metadata,
            holdings=filing_holdings
        )

    def parse_all_filings(self) -> List[ParsedFiling]:
        """
        Parse all filings with their holdings.

        Returns:
            List of ParsedFiling objects
        """
        # Load all filings and holdings
        all_filings = self.load_all_filings()
        all_holdings = self.load_all_holdings()

        # Group holdings by accession number
        holdings_by_filing: Dict[str, List[HoldingRecord]] = {}
        for holding in all_holdings:
            if holding.accession_number not in holdings_by_filing:
                holdings_by_filing[holding.accession_number] = []
            holdings_by_filing[holding.accession_number].append(holding)

        # Create ParsedFiling objects
        parsed_filings = []
        for accession_number, metadata in all_filings.items():
            filing_holdings = holdings_by_filing.get(accession_number, [])

            parsed_filing = ParsedFiling(
                metadata=metadata,
                holdings=filing_holdings
            )
            parsed_filings.append(parsed_filing)

        return parsed_filings

    def get_stats(self) -> Dict[str, int]:
        """
        Get statistics about the data.

        Returns:
            Dictionary with counts of filings, holdings, etc.
        """
        submissions = self._read_tsv('SUBMISSION.tsv')
        holdings = self._read_tsv('INFOTABLE.tsv')

        total_submissions = len(submissions)
        holdings_reports = sum(1 for row in submissions if row['SUBMISSIONTYPE'] == '13F-HR')
        notices = sum(1 for row in submissions if row['SUBMISSIONTYPE'] == '13F-NT')
        total_holdings = len(holdings)

        return {
            'total_submissions': total_submissions,
            '13f_holdings_reports': holdings_reports,
            '13f_notices': notices,
            'total_holdings': total_holdings,
        }
