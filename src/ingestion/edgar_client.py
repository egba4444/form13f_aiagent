"""SEC EDGAR API client for downloading Form 13F filings."""

import asyncio
import time
from pathlib import Path
from typing import List, Optional
from datetime import date, datetime

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from ..models import FilingMetadata


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
    ) -> List[FilingMetadata]:
        """
        Search for filings by CIK and date range.

        Args:
            cik: 10-digit Central Index Key
            form_type: "13F-HR" for institutional holdings
            date_from: Start date (inclusive)
            date_to: End date (inclusive)
            limit: Max results to return

        Returns:
            List of FilingMetadata objects

        Example:
            filings = await client.search_filings(
                cik="0001067983",
                date_from=date(2024, 1, 1)
            )
        """
        # TODO: Implement SEC EDGAR search
        # URL: https://www.sec.gov/cgi-bin/browse-edgar
        # Params: action=getcompany, CIK=, type=, dateb=, count=
        # Parse HTML table to extract accession numbers and dates
        raise NotImplementedError("Search filings - to be implemented in Phase 1")

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
