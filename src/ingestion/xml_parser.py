"""
Form 13F-HR XML Parser

Parses SEC Form 13F-HR XML filings and extracts text content sections.

Form 13F-HR structure:
- <edgarSubmission> root element
  - <formData> - Main form data
    - <coverPage> - Cover page information
      - <reportCalendarOrQuarter> - Filing period
      - <filingManager> - Manager details
      - <signatureBlock> - Signatures
    - <formData> can contain:
      - <informationTable> - Holdings data (we already have this from TSV)
      - <additionalInformation> - TEXT WE WANT
"""

import logging
from typing import Dict, List, Optional
from bs4 import BeautifulSoup, Tag
from pathlib import Path

logger = logging.getLogger(__name__)


class Form13FXMLParser:
    """Parser for Form 13F-HR XML filings."""

    def __init__(self):
        """Initialize parser."""
        pass

    def parse_file(self, xml_path: Path) -> Dict[str, List[Dict[str, str]]]:
        """
        Parse XML file and extract text sections.

        Args:
            xml_path: Path to XML file

        Returns:
            Dictionary with extracted text sections:
            {
                "accession_number": str,
                "sections": [
                    {"type": "cover_page_info", "text": "..."},
                    {"type": "explanatory_notes", "text": "..."},
                    ...
                ]
            }
        """
        try:
            # Extract accession number from filename (e.g., "0001067983-25-000001.xml")
            accession_from_filename = xml_path.stem  # Remove .xml extension

            with open(xml_path, 'r', encoding='utf-8') as f:
                xml_content = f.read()

            result = self.parse_string(xml_content)

            # Use accession from filename if not found in XML
            if not result.get("accession_number"):
                result["accession_number"] = accession_from_filename

            return result
        except Exception as e:
            logger.error(f"Error parsing file {xml_path}: {e}")
            return {"accession_number": None, "sections": []}

    def parse_string(self, xml_content: str) -> Dict[str, List[Dict[str, str]]]:
        """
        Parse XML content and extract text sections.

        Args:
            xml_content: XML string

        Returns:
            Dictionary with extracted text sections
        """
        try:
            # Parse XML with BeautifulSoup (handles malformed XML better than lxml)
            soup = BeautifulSoup(xml_content, 'xml')

            # Extract accession number
            accession_number = self._extract_accession_number(soup)

            # Extract text sections
            sections = []

            # 1. Cover page additional information
            cover_info = self._extract_cover_page_info(soup)
            if cover_info:
                sections.append({
                    "type": "cover_page_info",
                    "text": cover_info
                })

            # 2. Additional information / explanatory notes
            additional_info = self._extract_additional_information(soup)
            if additional_info:
                sections.append({
                    "type": "explanatory_notes",
                    "text": additional_info
                })

            # 3. Other included documents
            other_docs = self._extract_other_documents(soup)
            if other_docs:
                sections.append({
                    "type": "other_documents",
                    "text": other_docs
                })

            # 4. Amendment information
            amendment_info = self._extract_amendment_info(soup)
            if amendment_info:
                sections.append({
                    "type": "amendment_info",
                    "text": amendment_info
                })

            return {
                "accession_number": accession_number,
                "sections": sections
            }

        except Exception as e:
            logger.error(f"Error parsing XML content: {e}")
            return {"accession_number": None, "sections": []}

    def _extract_accession_number(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract accession number from XML."""
        # Look for <accessionNumber> tag
        acc_tag = soup.find("accessionNumber")
        if acc_tag:
            return acc_tag.get_text(strip=True)

        # Alternative: look in header
        header = soup.find("headerData")
        if header:
            acc_tag = header.find("accessionNumber")
            if acc_tag:
                return acc_tag.get_text(strip=True)

        return None

    def _extract_cover_page_info(self, soup: BeautifulSoup) -> Optional[str]:
        """
        Extract cover page textual information.

        This includes manager details, report information, etc.
        """
        texts = []

        # Find cover page
        cover_page = soup.find("coverPage")
        if not cover_page:
            return None

        # Filing manager name and address
        filing_manager = cover_page.find("filingManager")
        if filing_manager:
            name = filing_manager.find("name")
            if name:
                texts.append(f"Filing Manager: {name.get_text(strip=True)}")

            address = filing_manager.find("address")
            if address:
                street1 = address.find("street1")
                city = address.find("city")
                state_or_country = address.find("stateOrCountry")
                zipcode = address.find("zipCode")

                addr_parts = []
                if street1:
                    addr_parts.append(street1.get_text(strip=True))
                if city:
                    addr_parts.append(city.get_text(strip=True))
                if state_or_country:
                    addr_parts.append(state_or_country.get_text(strip=True))
                if zipcode:
                    addr_parts.append(zipcode.get_text(strip=True))

                if addr_parts:
                    texts.append(f"Address: {', '.join(addr_parts)}")

        # Report calendar or quarter
        report_period = cover_page.find("reportCalendarOrQuarter")
        if report_period:
            texts.append(f"Report Period: {report_period.get_text(strip=True)}")

        # Amendment info on cover page
        is_amendment = cover_page.find("isAmendment")
        if is_amendment and is_amendment.get_text(strip=True).lower() == "true":
            texts.append("This is an amendment filing")

            amendment_number = cover_page.find("amendmentNumber")
            if amendment_number:
                texts.append(f"Amendment Number: {amendment_number.get_text(strip=True)}")

        return "\n".join(texts) if texts else None

    def _extract_additional_information(self, soup: BeautifulSoup) -> Optional[str]:
        """
        Extract additional information / explanatory notes.

        This is the main source of qualitative text in 13F filings.
        """
        # Look for <additionalInformation> or <summaryPage><additionalInformation>
        additional_info = soup.find("additionalInformation")

        if additional_info:
            text = additional_info.get_text(strip=True)
            # Remove empty or whitespace-only content
            if text and len(text) > 10:
                return text

        return None

    def _extract_other_documents(self, soup: BeautifulSoup) -> Optional[str]:
        """
        Extract other included documents.

        Sometimes managers include additional documents or exhibits.
        """
        texts = []

        # Look for <documents> or <otherIncludedDocuments>
        documents = soup.find_all("otherIncludedDocuments")

        for doc in documents:
            doc_type = doc.find("type")
            doc_desc = doc.find("description")
            doc_text = doc.find("text")

            doc_parts = []
            if doc_type:
                doc_parts.append(f"Type: {doc_type.get_text(strip=True)}")
            if doc_desc:
                doc_parts.append(f"Description: {doc_desc.get_text(strip=True)}")
            if doc_text:
                doc_parts.append(doc_text.get_text(strip=True))

            if doc_parts:
                texts.append("\n".join(doc_parts))

        return "\n\n".join(texts) if texts else None

    def _extract_amendment_info(self, soup: BeautifulSoup) -> Optional[str]:
        """
        Extract amendment-specific information.

        When a filing is an amendment, there may be explanatory text about why.
        """
        texts = []

        # Check if this is an amendment
        is_amendment = soup.find("isAmendment")
        if not is_amendment or is_amendment.get_text(strip=True).lower() != "true":
            return None

        texts.append("=== AMENDMENT FILING ===")

        # Amendment number
        amendment_num = soup.find("amendmentNumber")
        if amendment_num:
            texts.append(f"Amendment Number: {amendment_num.get_text(strip=True)}")

        # Amendment type
        amendment_type = soup.find("amendmentType")
        if amendment_type:
            texts.append(f"Amendment Type: {amendment_type.get_text(strip=True)}")

        # Reason for amendment (if provided in additional information)
        # This is often where managers explain what changed
        additional_info = soup.find("additionalInformation")
        if additional_info:
            text = additional_info.get_text(strip=True)
            if "amend" in text.lower() or "correct" in text.lower():
                texts.append(f"\nReason for Amendment:\n{text}")

        return "\n".join(texts) if len(texts) > 1 else None

    def extract_metadata(self, xml_content: str) -> Dict[str, str]:
        """
        Extract metadata from XML (without full parsing).

        Useful for quick validation.

        Returns:
            Dictionary with metadata: accession_number, period, is_amendment, etc.
        """
        soup = BeautifulSoup(xml_content, 'xml')

        metadata = {}

        # Accession number
        acc = self._extract_accession_number(soup)
        if acc:
            metadata["accession_number"] = acc

        # Period
        period = soup.find("reportCalendarOrQuarter")
        if period:
            metadata["period"] = period.get_text(strip=True)

        # Is amendment
        is_amend = soup.find("isAmendment")
        if is_amend:
            metadata["is_amendment"] = is_amend.get_text(strip=True).lower() == "true"
        else:
            metadata["is_amendment"] = False

        # Manager CIK
        cik = soup.find("cik")
        if cik:
            metadata["cik"] = cik.get_text(strip=True)

        return metadata


# Example usage
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python xml_parser.py <path_to_xml_file>")
        sys.exit(1)

    xml_file = Path(sys.argv[1])

    if not xml_file.exists():
        print(f"File not found: {xml_file}")
        sys.exit(1)

    parser = Form13FXMLParser()
    result = parser.parse_file(xml_file)

    print("="*60)
    print(f"Accession Number: {result['accession_number']}")
    print("="*60)

    if result['sections']:
        print(f"\nExtracted {len(result['sections'])} text sections:\n")

        for section in result['sections']:
            print(f"--- {section['type'].upper()} ---")
            print(section['text'][:500] + "..." if len(section['text']) > 500 else section['text'])
            print(f"\n(Length: {len(section['text'])} characters)\n")
    else:
        print("\nNo text sections found in this filing.")
