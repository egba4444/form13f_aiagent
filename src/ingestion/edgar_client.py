"""SEC EDGAR API client for downloading Form 13F and 10-K filings."""

import asyncio
import time
from pathlib import Path
from typing import List, Optional
from datetime import date, datetime
import logging
from dataclasses import dataclass

import httpx
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

from ..models import FilingMetadata

logger = logging.getLogger(__name__)


@dataclass
class Filing10KMetadata:
    """Simplified metadata for 10-K filings."""
    accession_number: str
    cik: str
    filing_date: date
    form_type: str


class SECEdgarClient:
    """
    Client for SEC EDGAR API with rate limiting and caching.

    SEC Requirements:
    - Max 10 requests per second
    - Must include User-Agent with company name and email
    """

    BASE_URL = "https://www.sec.gov"

    def __init__(self, user_agent: str, cache_dir: Optional[Path] = None):
        """
        Initialize EDGAR client.

        Args:
            user_agent: Format: "CompanyName contact@email.com"
            cache_dir: Directory to cache downloaded filings
        """
        self.user_agent = user_agent
        self.cache_dir = cache_dir or Path("data/raw")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.session = httpx.AsyncClient(
            headers={"User-Agent": user_agent},
            timeout=30.0,
            follow_redirects=True
        )

        self.last_request_time = 0
        self.min_interval = 0.1  # 10 requests/second

    async def _rate_limit(self):
        """Enforce 10 req/sec rate limit."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_interval:
            await asyncio.sleep(self.min_interval - elapsed)
        self.last_request_time = time.time()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def _fetch(self, url: str) -> str:
        """
        Fetch URL with retry logic.

        Args:
            url: Full URL to fetch

        Returns:
            Response text

        Raises:
            httpx.HTTPStatusError: On HTTP errors
        """
        await self._rate_limit()
        response = await self.session.get(url)
        response.raise_for_status()
        return response.text

    async def search_filings(
        self,
        cik: str,
        form_type: str = "13F-HR",
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        limit: int = 100
    ) -> List[Filing10KMetadata]:
        """
        Search for filings by CIK and date range.

        Args:
            cik: 10-digit Central Index Key
            form_type: "13F-HR" or "10-K"
            date_from: Start date (inclusive)
            date_to: End date (inclusive)
            limit: Max results to return

        Returns:
            List of Filing10KMetadata objects

        Example:
            filings = await client.search_filings(
                cik="0001067983",
                form_type="10-K",
                date_from=date(2024, 1, 1)
            )
        """
        # Clean CIK (remove leading zeros for URL)
        cik_clean = cik.lstrip("0")

        # Build query params
        params = {
            "action": "getcompany",
            "CIK": cik_clean,
            "type": form_type,
            "dateb": date_to.strftime("%Y%m%d") if date_to else "",
            "owner": "exclude",
            "count": min(limit, 100)  # SEC max is 100
        }

        # Fetch search results page
        url = f"{self.BASE_URL}/cgi-bin/browse-edgar"
        logger.info(f"Searching filings: CIK={cik}, type={form_type}, limit={limit}")

        html = await self._fetch(url + "?" + "&".join(f"{k}={v}" for k, v in params.items()))

        # Parse HTML table
        soup = BeautifulSoup(html, 'html.parser')
        filing_table = soup.find("table", class_="tableFile2")

        if not filing_table:
            logger.warning(f"No filings table found for CIK {cik}")
            return []

        filings = []
        for row in filing_table.find_all("tr")[1:]:  # Skip header row
            cols = row.find_all("td")
            if len(cols) < 5:
                continue

            try:
                # Column structure: Filing Type, Filing Date, Documents, Description
                filing_type = cols[0].text.strip()
                filing_date_str = cols[3].text.strip()
                filing_date_obj = datetime.strptime(filing_date_str, "%Y-%m-%d").date()

                # Extract accession number from documents link
                doc_link = cols[1].find("a", id="documentsbutton")
                if doc_link:
                    # Link format: /Archives/edgar/data/320193/000032019324000123-index.htm
                    href = doc_link["href"]
                    accession = href.split("/")[-1].replace("-index.htm", "")

                    filings.append(Filing10KMetadata(
                        accession_number=accession,
                        cik=cik.zfill(10),  # Restore padded format
                        filing_date=filing_date_obj,
                        form_type=filing_type
                    ))
            except Exception as e:
                logger.warning(f"Error parsing row: {e}")
                continue

        # Filter by date range if specified
        if date_from:
            filings = [f for f in filings if f.filing_date >= date_from]

        logger.info(f"Found {len(filings)} filings for CIK {cik}")
        return filings[:limit]

    async def download_filing(self, accession_number: str) -> str:
        """
        Download a specific filing by accession number.

        Args:
            accession_number: SEC filing identifier (e.g., "0001067983-25-000001")

        Returns:
            XML content of the filing

        Example:
            xml = await client.download_filing("0001067983-25-000001")
        """
        # Check cache first
        cache_file = self._get_cache_path(accession_number)
        if cache_file.exists():
            return cache_file.read_text()

        # TODO: Implement filing download
        # 1. Get filing index page
        # 2. Parse to find primary document URL (usually .xml)
        # 3. Download XML
        # 4. Save to cache
        # 5. Return content
        raise NotImplementedError("Download filing - to be implemented in Phase 1")

    async def download_10k_filing(self, accession_number: str, cik: str) -> str:
        """
        Download Form 10-K primary document (HTML).

        10-K filings are multi-document with an index page listing all files.
        This method downloads the primary 10-K HTML document.

        Args:
            accession_number: SEC filing identifier (e.g., "0000320193-23-000077")
            cik: Company CIK (10-digit padded)

        Returns:
            HTML content of the primary 10-K document

        Example:
            html = await client.download_10k_filing("0000320193-23-000077", "0000320193")
        """
        # Check cache first
        cache_file = self._get_10k_cache_path(accession_number)
        if cache_file.exists():
            logger.info(f"Loading 10-K from cache: {accession_number}")
            return cache_file.read_text()

        logger.info(f"Downloading 10-K: {accession_number} for CIK {cik}")

        # Step 1: Fetch index page
        cik_clean = cik.lstrip("0")
        accession_clean = accession_number.replace("-", "")
        index_url = f"{self.BASE_URL}/Archives/edgar/data/{cik_clean}/{accession_clean}/{accession_number}-index.htm"

        logger.debug(f"Fetching index: {index_url}")
        index_html = await self._fetch(index_url)

        # Step 2: Parse index to find primary document
        soup = BeautifulSoup(index_html, 'html.parser')

        # Find table with document list
        table = soup.find("table", summary="Document Format Files")
        if not table:
            # Try alternative table format
            table = soup.find("table", class_="tableFile")

        if not table:
            raise ValueError(f"No document table found in index for {accession_number}")

        # Step 3: Find primary 10-K document
        # Look for .htm or .html file (not .xml, not exhibits)
        primary_doc_link = None

        for row in table.find_all("tr"):
            cols = row.find_all("td")
            if len(cols) >= 4:
                # Get document filename and type
                link = cols[2].find("a")  # Document link is usually in 3rd column
                if not link:
                    continue

                filename = link.text.strip().lower()
                doc_type = cols[3].text.strip() if len(cols) > 3 else ""

                # Look for HTML document (not XML, not exhibits)
                # Prefer files ending in .htm or .html that are the primary document
                if (filename.endswith('.htm') or filename.endswith('.html')) and \
                   '10-k' in doc_type.lower() and \
                   'ex-' not in doc_type.lower() and \
                   'graphic' not in doc_type.lower():
                    href = link["href"]

                    # Handle iXBRL viewer links: /ix?doc=/Archives/edgar/...
                    # Extract the actual document URL from the doc parameter
                    if href.startswith('/ix?doc='):
                        primary_doc_link = href.split('doc=')[1]
                    else:
                        primary_doc_link = href

                    logger.debug(f"Found primary doc: {filename} ({doc_type})")
                    break

        # Fallback: if no specific HTML file found, try first .htm file
        if not primary_doc_link:
            for row in table.find_all("tr"):
                cols = row.find_all("td")
                if len(cols) >= 3:
                    link = cols[2].find("a")
                    if link:
                        filename = link.text.strip().lower()
                        if filename.endswith('.htm') or filename.endswith('.html'):
                            primary_doc_link = link["href"]
                            logger.debug(f"Fallback: using {filename}")
                            break

        if not primary_doc_link:
            raise ValueError(f"Primary 10-K document not found for {accession_number}")

        # Step 4: Download primary document
        doc_url = f"{self.BASE_URL}{primary_doc_link}"
        logger.debug(f"Downloading primary doc: {doc_url}")
        html_content = await self._fetch(doc_url)

        # Step 5: Save to cache
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(html_content)
        logger.info(f"Cached 10-K: {cache_file}")

        return html_content

    def _get_10k_cache_path(self, accession_number: str) -> Path:
        """Get cache file path for a 10-K filing."""
        return self.cache_dir / "10k" / f"{accession_number}.html"

    def _get_cache_path(self, accession_number: str) -> Path:
        """Get cache file path for an accession number."""
        # Format: data/raw/2024/Q4/0001067983-25-000001.xml
        # Extract year from accession number
        return self.cache_dir / f"{accession_number}.xml"

    async def close(self):
        """Close HTTP session."""
        await self.session.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
