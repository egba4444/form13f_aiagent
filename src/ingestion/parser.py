"""XML parser for Form 13F-HR filings."""

from datetime import datetime
from typing import List, Optional
from lxml import etree

from ..models import FilingMetadata, HoldingRecord, ParsedFiling


class Form13FParser:
    """
    Parses SEC Form 13F-HR XML filings.

    Handles multiple XML schema versions (1.6, 1.7).
    """

    def parse(self, xml_content: str) -> ParsedFiling:
        """
        Parse Form 13F XML into structured data.

        Args:
            xml_content: Raw XML string from SEC EDGAR

        Returns:
            ParsedFiling with metadata and holdings

        Example:
            parser = Form13FParser()
            parsed = parser.parse(xml_content)
            print(f"Manager: {parsed.metadata.manager_name}")
            print(f"Holdings: {len(parsed.holdings)}")
        """
        tree = etree.fromstring(xml_content.encode('utf-8'))

        return ParsedFiling(
            metadata=self._parse_metadata(tree),
            holdings=self._parse_holdings(tree),
            commentary_text=self._extract_commentary(tree),
            raw_xml=xml_content
        )

    def _parse_metadata(self, tree: etree._Element) -> FilingMetadata:
        """
        Extract filing metadata from cover page.

        XML structure:
        <edgarSubmission>
          <formData>
            <coverPage>
              <filingManager><name>...</name><cik>...</cik></filingManager>
              <reportCalendarOrQuarter>...</reportCalendarOrQuarter>
              <summaryPage>
                <tableValueTotal>...</tableValueTotal>
                <tableEntryTotal>...</tableEntryTotal>
              </summaryPage>
            </coverPage>
          </formData>
        </edgarSubmission>
        """
        # TODO: Implement metadata extraction
        # 1. Find <filingManager> element
        # 2. Extract CIK and manager name
        # 3. Extract period_of_report from <reportCalendarOrQuarter>
        # 4. Extract total value from <tableValueTotal>
        # 5. Extract accession number from document attributes
        raise NotImplementedError("Parse metadata - to be implemented in Phase 1")

    def _parse_holdings(self, tree: etree._Element) -> List[HoldingRecord]:
        """
        Extract holdings from information table.

        XML structure:
        <informationTable>
          <infoTable>
            <nameOfIssuer>APPLE INC</nameOfIssuer>
            <titleOfClass>COM</titleOfClass>
            <cusip>037833100</cusip>
            <value>157000000</value>
            <shrsOrPrnAmt>
              <sshPrnamt>916000000</sshPrnamt>
              <sshPrnamtType>SH</sshPrnamtType>
            </shrsOrPrnAmt>
            <investmentDiscretion>SOLE</investmentDiscretion>
            <votingAuthority>
              <Sole>916000000</Sole>
              <Shared>0</Shared>
              <None>0</None>
            </votingAuthority>
          </infoTable>
          ...
        </informationTable>
        """
        holdings = []

        # TODO: Implement holdings extraction
        # 1. Find all <infoTable> elements
        # 2. For each, extract:
        #    - CUSIP
        #    - issuer_name
        #    - value_thousands
        #    - shares_or_principal
        #    - investment_discretion
        #    - voting authority
        # 3. Validate CUSIP format
        # 4. Create HoldingRecord objects

        return holdings

    def _extract_commentary(self, tree: etree._Element) -> Optional[str]:
        """
        Extract explanatory notes and commentary.

        This will be used in Phase 7 for RAG.
        For now, just extract and store the text.
        """
        # TODO: Extract commentary sections
        # Look for:
        # - <otherIncludedManagersInfo>
        # - <explanatoryNotes>
        # - Free-form text after signature
        return None

    def _get_text(self, element: etree._Element, xpath: str) -> Optional[str]:
        """Helper to extract text from XPath."""
        result = element.find(xpath)
        return result.text.strip() if result is not None and result.text else None

    def _get_int(self, element: etree._Element, xpath: str, default: int = 0) -> int:
        """Helper to extract integer from XPath."""
        text = self._get_text(element, xpath)
        return int(text) if text else default

    def _parse_date(self, date_str: str) -> datetime:
        """Parse date string (MM-DD-YYYY format)."""
        return datetime.strptime(date_str, "%m-%d-%Y").date()
