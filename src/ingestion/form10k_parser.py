"""
Form 10-K HTML Parser

Extracts text sections from SEC Form 10-K annual reports.

Key Sections Extracted:
- Item 1: Business
- Item 1A: Risk Factors
- Item 1B: Unresolved Staff Comments
- Item 2: Properties
- Item 3: Legal Proceedings
- Item 7: Management's Discussion and Analysis (MD&A)
- Item 7A: Quantitative and Qualitative Disclosures About Market Risk
- Item 8: Financial Statements and Supplementary Data

Usage:
    parser = Form10KParser()
    sections = parser.parse_html(html_content)

    for section_name, text in sections.items():
        print(f"{section_name}: {len(text)} characters")
"""

import re
import logging
from typing import Dict, Optional
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class Form10KParser:
    """Parser for Form 10-K HTML filings."""

    # Section patterns for extraction (regex patterns)
    ITEM_PATTERNS = {
        "Item 1": r"item\s*1[^a-z0-9\.].*?business",
        "Item 1A": r"item\s*1a.*?risk\s*factors",
        "Item 1B": r"item\s*1b.*?unresolved\s*staff",
        "Item 2": r"item\s*2[^a-z0-9\.].*?properties",
        "Item 3": r"item\s*3[^a-z0-9\.].*?legal\s*proceedings",
        "Item 7": r"item\s*7[^a-z0-9\.].*?management.*?discussion",
        "Item 7A": r"item\s*7a.*?market\s*risk",
        "Item 8": r"item\s*8[^a-z0-9\.].*?financial\s*statements"
    }

    # Minimum characters for a valid section
    MIN_SECTION_LENGTH = 500

    def parse_html(self, html_content: str) -> Dict[str, str]:
        """
        Parse 10-K HTML and extract text sections.

        Args:
            html_content: Raw HTML content of 10-K filing

        Returns:
            Dictionary with section names as keys and cleaned text as values

        Example:
            >>> parser = Form10KParser()
            >>> sections = parser.parse_html(html_content)
            >>> print(sections.keys())
            dict_keys(['Item 1', 'Item 1A', 'Item 7'])
        """
        logger.info("Parsing 10-K HTML document...")

        # Parse HTML
        soup = BeautifulSoup(html_content, 'html.parser')

        # Remove unwanted tags
        for tag in soup(['script', 'style', 'meta', 'link', 'noscript']):
            tag.decompose()

        # Get full text
        full_text = soup.get_text()

        # Extract sections
        sections = {}
        for item_name, pattern in self.ITEM_PATTERNS.items():
            text = self._extract_section(full_text, item_name, pattern)
            if text:
                sections[item_name] = text
                logger.info(f"  ✓ Extracted {item_name}: {len(text):,} characters")
            else:
                logger.warning(f"  ✗ Failed to extract {item_name}")

        logger.info(f"Successfully extracted {len(sections)}/{len(self.ITEM_PATTERNS)} sections")
        return sections

    def _extract_section(self, full_text: str, item_name: str, pattern: str) -> Optional[str]:
        """
        Extract a specific Item section from full text.

        Strategy:
        1. Find start of section using regex pattern (skip TOC matches)
        2. Find end (next Item header or end of document)
        3. Extract text between start and end
        4. Clean and normalize

        Args:
            full_text: Complete 10-K text
            item_name: Section name (e.g., "Item 1A")
            pattern: Regex pattern to find section start

        Returns:
            Cleaned section text or None if not found/too short
        """
        # Find all matches for the section
        matches = list(re.finditer(pattern, full_text, re.IGNORECASE))
        if not matches:
            logger.debug(f"Section {item_name} not found with pattern: {pattern}")
            return None

        # Strategy: Try each match and return the first one that yields a valid section
        # This helps skip TOC entries which are typically short
        for match in matches:
            start_idx = match.start()

            # Find section end (next Item or end of doc)
            end_idx = len(full_text)

            # Look for next Item header
            # Use stricter pattern: must be at start of line or after significant whitespace
            # This avoids matching "Part II, Item 7" references within text
            next_item_pattern = r"(?:^|\n)\s*item\s*\d+[abc]?[^a-z0-9\.]"
            next_match = re.search(next_item_pattern, full_text[start_idx + 100:], re.IGNORECASE | re.MULTILINE)
            if next_match:
                end_idx = start_idx + 100 + next_match.start()

            # Extract and clean
            section_text = full_text[start_idx:end_idx]
            section_text = self._clean_text(section_text)

            # Validate minimum length - if valid, return it
            if len(section_text) >= self.MIN_SECTION_LENGTH:
                return section_text

            # Otherwise try next match
            logger.debug(f"Section {item_name} match at {start_idx} too short ({len(section_text)} chars), trying next match")

        # No valid section found
        logger.debug(f"Section {item_name} not found with sufficient content (min={self.MIN_SECTION_LENGTH})")
        return None

    def _clean_text(self, text: str) -> str:
        """
        Clean extracted text.

        Removes:
        - Excessive whitespace
        - Page numbers
        - Table of contents entries
        - Special characters and artifacts

        Args:
            text: Raw extracted text

        Returns:
            Cleaned text
        """
        # Remove page numbers (e.g., "Page 12", "12 | Page")
        text = re.sub(r'page\s+\d+', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\d+\s*\|\s*page', '', text, flags=re.IGNORECASE)

        # Remove table of contents dots (e.g., "Introduction ..... 5")
        text = re.sub(r'\.{3,}', '', text)

        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)

        # Remove form feed and other special chars
        text = re.sub(r'[\x0c\x0b]', '', text)

        # Remove multiple consecutive dashes
        text = re.sub(r'-{3,}', '', text)

        # Strip leading/trailing whitespace
        text = text.strip()

        return text

    def extract_metadata(self, html_content: str) -> Dict[str, str]:
        """
        Extract metadata from 10-K filing.

        Args:
            html_content: Raw HTML content

        Returns:
            Dictionary with metadata fields

        Note: This is a basic implementation. Can be enhanced with more fields.
        """
        soup = BeautifulSoup(html_content, 'html.parser')

        metadata = {}

        # Try to find company name
        company_tag = soup.find("span", class_="companyName")
        if company_tag:
            metadata["company_name"] = company_tag.text.strip()

        # Try to find fiscal year
        fy_tag = soup.find(text=re.compile("fiscal year end", re.IGNORECASE))
        if fy_tag:
            metadata["fiscal_year"] = fy_tag.strip()

        return metadata
