"""
SEC EDGAR XML Downloader

Downloads Form 13F-HR XML filings from SEC EDGAR based on accession numbers
in the database. Implements SEC's rate limiting requirements (10 requests/second).

Usage:
    python -m src.ingestion.edgar_xml_downloader --quarter 2024-Q4
    python -m src.ingestion.edgar_xml_downloader --manager-cik 0001067983 --limit 10
"""

import os
import time
import argparse
import logging
from pathlib import Path
from typing import List, Tuple, Optional
from datetime import datetime
import httpx
from tqdm import tqdm
from sqlalchemy import create_engine, text

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# SEC EDGAR base URL for Archives
SEC_EDGAR_BASE = "https://www.sec.gov/Archives/edgar/data"

# Rate limiting: SEC allows 10 requests per second
RATE_LIMIT_DELAY = 0.11  # 110ms between requests (slightly conservative)

# User agent (SEC requires identification)
USER_AGENT = "Form13F AI Agent hodolhodol0@gmail.com"


class EdgarXMLDownloader:
    """Download 13F-HR XML filings from SEC EDGAR."""

    def __init__(self, database_url: str, output_dir: str = "data/xml_filings"):
        """
        Initialize downloader.

        Args:
            database_url: PostgreSQL connection string
            output_dir: Directory to save XML files
        """
        self.database_url = database_url
        self.output_dir = Path(output_dir)
        self.engine = create_engine(database_url)

        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # HTTP client with proper headers
        self.client = httpx.Client(
            headers={
                "User-Agent": USER_AGENT,
                "Accept-Encoding": "gzip, deflate",
                "Host": "www.sec.gov"
            },
            timeout=30.0,
            follow_redirects=True
        )

        # Statistics
        self.stats = {
            "attempted": 0,
            "successful": 0,
            "failed": 0,
            "skipped": 0
        }

    def get_filings_to_download(
        self,
        quarter: Optional[str] = None,
        manager_cik: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Tuple[str, str, str, str]]:
        """
        Get list of filings to download from database.

        Args:
            quarter: Filter by quarter (e.g., "2024-Q4")
            manager_cik: Filter by specific manager CIK
            limit: Maximum number of filings to download

        Returns:
            List of tuples: (accession_number, cik, period_of_report, filing_date)
        """
        query = """
            SELECT
                f.accession_number,
                f.cik,
                f.period_of_report,
                f.filing_date
            FROM filings f
            WHERE 1=1
        """

        params = {}

        if quarter:
            # Parse quarter (e.g., "2024-Q4" -> year=2024, quarter=4)
            year, q = quarter.split("-Q")
            quarter_num = int(q)

            # Map quarter to end dates
            quarter_end_dates = {
                1: f"{year}-03-31",
                2: f"{year}-06-30",
                3: f"{year}-09-30",
                4: f"{year}-12-31"
            }

            query += " AND f.period_of_report = :period"
            params["period"] = quarter_end_dates[quarter_num]

        if manager_cik:
            query += " AND f.cik = :cik"
            params["cik"] = manager_cik

        query += " ORDER BY f.filing_date DESC"

        if limit:
            query += " LIMIT :limit"
            params["limit"] = limit

        with self.engine.connect() as conn:
            result = conn.execute(text(query), params)
            return result.fetchall()

    def get_xml_file_path(self, accession_number: str, period_of_report) -> Path:
        """
        Get local file path for an XML filing.

        Args:
            accession_number: SEC accession number
            period_of_report: Filing period date (str or date object)

        Returns:
            Path to XML file
        """
        # Extract year and quarter from period
        # Handle both string and date objects
        if isinstance(period_of_report, str):
            period_date = datetime.strptime(period_of_report, "%Y-%m-%d")
        else:
            # Already a date object
            period_date = period_of_report

        year = period_date.year
        quarter = f"Q{(period_date.month - 1) // 3 + 1}"

        # Create directory structure: data/xml_filings/2024/Q4/
        filing_dir = self.output_dir / str(year) / quarter
        filing_dir.mkdir(parents=True, exist_ok=True)

        # File name: accession number with .xml extension
        return filing_dir / f"{accession_number}.xml"

    def download_xml(self, accession_number: str, cik: str) -> Optional[str]:
        """
        Download XML filing from SEC EDGAR.

        Args:
            accession_number: SEC accession number (e.g., "0001067983-25-000001")
            cik: Manager CIK

        Returns:
            XML content as string, or None if download failed
        """
        # SEC EDGAR URL format (updated to use Archives)
        # https://www.sec.gov/Archives/edgar/data/{cik}/{accession-no-dashes}/primary_doc.xml

        # Remove dashes from accession number for URL
        accession_no_dashes = accession_number.replace("-", "")

        # Remove leading zeros from CIK for URL path
        cik_no_leading_zeros = cik.lstrip("0")

        url = f"{SEC_EDGAR_BASE}/{cik_no_leading_zeros}/{accession_no_dashes}/primary_doc.xml"

        try:
            response = self.client.get(url)
            response.raise_for_status()

            # Check if we got XML (not HTML error page)
            content = response.text
            if content.strip().startswith("<?xml") or "<XML>" in content.upper():
                return content
            else:
                logger.warning(f"Response is not XML for {accession_number}")
                return None

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error downloading {accession_number}: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error downloading {accession_number}: {e}")
            return None

    def download_filings(
        self,
        quarter: Optional[str] = None,
        manager_cik: Optional[str] = None,
        limit: Optional[int] = None,
        skip_existing: bool = True
    ):
        """
        Download XML filings and save to disk.

        Args:
            quarter: Filter by quarter (e.g., "2024-Q4")
            manager_cik: Filter by specific manager CIK
            limit: Maximum number of filings to download
            skip_existing: Skip files that already exist
        """
        logger.info("Fetching filings from database...")
        filings = self.get_filings_to_download(quarter, manager_cik, limit)

        if not filings:
            logger.warning("No filings found matching criteria")
            return

        logger.info(f"Found {len(filings)} filings to process")

        # Progress bar
        pbar = tqdm(filings, desc="Downloading XMLs", unit="filing")

        for accession_number, cik, period_of_report, filing_date in pbar:
            self.stats["attempted"] += 1

            # Check if file already exists
            xml_path = self.get_xml_file_path(accession_number, period_of_report)

            if skip_existing and xml_path.exists():
                self.stats["skipped"] += 1
                pbar.set_postfix({
                    "success": self.stats["successful"],
                    "failed": self.stats["failed"],
                    "skipped": self.stats["skipped"]
                })
                continue

            # Download XML
            xml_content = self.download_xml(accession_number, cik)

            if xml_content:
                # Save to file
                xml_path.write_text(xml_content, encoding="utf-8")
                self.stats["successful"] += 1
                logger.debug(f"Downloaded: {accession_number}")
            else:
                self.stats["failed"] += 1
                logger.warning(f"Failed to download: {accession_number}")

            # Update progress bar
            pbar.set_postfix({
                "success": self.stats["successful"],
                "failed": self.stats["failed"],
                "skipped": self.stats["skipped"]
            })

            # Rate limiting: Wait between requests
            time.sleep(RATE_LIMIT_DELAY)

        # Print summary
        logger.info("\n" + "="*60)
        logger.info("Download Summary")
        logger.info("="*60)
        logger.info(f"Attempted:  {self.stats['attempted']}")
        logger.info(f"Successful: {self.stats['successful']}")
        logger.info(f"Failed:     {self.stats['failed']}")
        logger.info(f"Skipped:    {self.stats['skipped']}")
        logger.info("="*60)

    def close(self):
        """Clean up resources."""
        self.client.close()


def main():
    """Command-line interface."""
    parser = argparse.ArgumentParser(
        description="Download Form 13F-HR XML filings from SEC EDGAR"
    )

    parser.add_argument(
        "--quarter",
        type=str,
        help="Quarter to download (e.g., 2024-Q4)"
    )

    parser.add_argument(
        "--manager-cik",
        type=str,
        help="Download only filings for specific manager CIK"
    )

    parser.add_argument(
        "--limit",
        type=int,
        help="Maximum number of filings to download (for testing)"
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/xml_filings",
        help="Output directory for XML files (default: data/xml_filings)"
    )

    parser.add_argument(
        "--no-skip-existing",
        action="store_true",
        help="Re-download files that already exist"
    )

    args = parser.parse_args()

    # Get database URL from environment
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logger.error("DATABASE_URL environment variable not set")
        return

    # Create downloader
    downloader = EdgarXMLDownloader(
        database_url=database_url,
        output_dir=args.output_dir
    )

    try:
        # Download filings
        downloader.download_filings(
            quarter=args.quarter,
            manager_cik=args.manager_cik,
            limit=args.limit,
            skip_existing=not args.no_skip_existing
        )
    finally:
        downloader.close()


if __name__ == "__main__":
    main()
