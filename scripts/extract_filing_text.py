"""
Text Extraction Pipeline for Form 13F Filings

This script orchestrates the complete text extraction workflow:
1. Downloads XML filings from SEC EDGAR
2. Parses XML to extract text sections
3. Stores extracted text in database
4. Optionally cleans up XML files after processing

Usage:
    # Process all filings
    python scripts/extract_filing_text.py

    # Process specific quarter
    python scripts/extract_filing_text.py --quarter 2024-Q4

    # Process with custom limit
    python scripts/extract_filing_text.py --limit 100

    # Keep XML files after processing
    python scripts/extract_filing_text.py --keep-xml

    # Process only filings without text content
    python scripts/extract_filing_text.py --skip-existing
"""

import os
import sys
import logging
import argparse
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ingestion.edgar_xml_downloader import EdgarXMLDownloader
from src.ingestion.xml_parser import Form13FXMLParser

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class TextExtractionPipeline:
    """Orchestrates the complete text extraction workflow."""

    def __init__(
        self,
        database_url: str,
        output_dir: str = "data/xml_filings",
        keep_xml: bool = False
    ):
        """
        Initialize the pipeline.

        Args:
            database_url: PostgreSQL connection string
            output_dir: Directory to store downloaded XMLs
            keep_xml: Whether to keep XML files after processing
        """
        self.database_url = database_url
        self.output_dir = Path(output_dir)
        self.keep_xml = keep_xml

        # Initialize components
        self.downloader = EdgarXMLDownloader(database_url, str(output_dir))
        self.parser = Form13FXMLParser()

        logger.info(f"Pipeline initialized")
        logger.info(f"  Output directory: {output_dir}")
        logger.info(f"  Keep XML files: {keep_xml}")

    def run(
        self,
        quarter: Optional[str] = None,
        limit: Optional[int] = None,
        skip_existing: bool = True
    ) -> Dict[str, int]:
        """
        Run the complete extraction pipeline.

        Args:
            quarter: Specific quarter to process (e.g., "2024-Q4")
            limit: Maximum number of filings to process
            skip_existing: Skip filings that already have text content

        Returns:
            Dictionary with statistics
        """
        logger.info("=" * 80)
        logger.info("STARTING TEXT EXTRACTION PIPELINE")
        logger.info("=" * 80)

        stats = {
            "xml_downloaded": 0,
            "xml_failed": 0,
            "xml_skipped": 0,
            "files_parsed": 0,
            "sections_inserted": 0,
            "sections_failed": 0,
            "xml_deleted": 0
        }

        # Step 1: Download XML filings
        logger.info("\nStep 1: Downloading XML filings from SEC EDGAR...")
        self.downloader.download_filings(
            quarter=quarter,
            limit=limit,
            skip_existing=skip_existing
        )

        # Get statistics from downloader
        # (Note: We'd need to modify the downloader to return stats)

        # Step 2: Find all XML files
        logger.info("\nStep 2: Finding downloaded XML files...")
        xml_files = list(self.output_dir.rglob("*.xml"))
        logger.info(f"Found {len(xml_files)} XML files to process")

        if not xml_files:
            logger.warning("No XML files found. Exiting.")
            return stats

        # Step 3: Parse XML files
        logger.info("\nStep 3: Parsing XML files...")
        parsed_results = []

        for i, xml_file in enumerate(xml_files, 1):
            try:
                logger.info(f"  [{i}/{len(xml_files)}] Parsing {xml_file.name}...")
                result = self.parser.parse_file(xml_file)

                if result.get("accession_number") and result.get("sections"):
                    parsed_results.append(result)
                    stats["files_parsed"] += 1
                    logger.info(f"    Found {len(result['sections'])} text sections")
                else:
                    logger.warning(f"    No sections found in {xml_file.name}")

            except Exception as e:
                logger.error(f"    Error parsing {xml_file.name}: {e}")

        logger.info(f"\nSuccessfully parsed {stats['files_parsed']} files")

        # Step 4: Insert into database
        if parsed_results:
            logger.info("\nStep 4: Inserting text sections into database...")
            inserted, failed = self._insert_text_sections(parsed_results)
            stats["sections_inserted"] = inserted
            stats["sections_failed"] = failed
            logger.info(f"  Inserted: {inserted}")
            logger.info(f"  Failed: {failed}")
        else:
            logger.warning("\nStep 4: No parsed results to insert")

        # Step 5: Clean up XML files if requested
        if not self.keep_xml:
            logger.info("\nStep 5: Cleaning up XML files...")
            for xml_file in xml_files:
                try:
                    xml_file.unlink()
                    stats["xml_deleted"] += 1
                except Exception as e:
                    logger.error(f"  Error deleting {xml_file.name}: {e}")
            logger.info(f"  Deleted {stats['xml_deleted']} XML files")
        else:
            logger.info("\nStep 5: Keeping XML files (--keep-xml flag set)")

        # Print summary
        self._print_summary(stats)

        return stats

    def _insert_text_sections(self, parsed_results: List[Dict]) -> tuple[int, int]:
        """
        Insert extracted text sections into database.

        Args:
            parsed_results: List of parsed filing results

        Returns:
            Tuple of (inserted_count, failed_count)
        """
        inserted = 0
        failed = 0

        try:
            conn = psycopg2.connect(self.database_url)
            cur = conn.cursor()

            # Prepare data for bulk insert
            records = []
            for result in parsed_results:
                accession_number = result.get("accession_number")
                sections = result.get("sections", [])

                if not accession_number or not sections:
                    continue

                for section in sections:
                    records.append((
                        accession_number,
                        section["type"],
                        section["text"],
                        False,  # xml_stored
                        None    # xml_storage_path
                    ))

            if records:
                # Use INSERT ... ON CONFLICT to handle duplicates
                insert_query = """
                    INSERT INTO filing_text_content
                        (accession_number, content_type, text_content, xml_stored, xml_storage_path)
                    VALUES %s
                    ON CONFLICT (accession_number, content_type)
                    DO UPDATE SET
                        text_content = EXCLUDED.text_content,
                        extracted_at = NOW()
                    RETURNING id
                """

                try:
                    execute_values(cur, insert_query, records)
                    inserted = cur.rowcount
                    conn.commit()
                except Exception as e:
                    logger.error(f"Error inserting records: {e}")
                    conn.rollback()
                    failed = len(records)

            cur.close()
            conn.close()

        except Exception as e:
            logger.error(f"Database error: {e}")
            failed = len(parsed_results)

        return inserted, failed

    def _print_summary(self, stats: Dict[str, int]):
        """Print pipeline execution summary."""
        logger.info("\n" + "=" * 80)
        logger.info("PIPELINE EXECUTION SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Files parsed:        {stats['files_parsed']}")
        logger.info(f"Sections inserted:   {stats['sections_inserted']}")
        logger.info(f"Sections failed:     {stats['sections_failed']}")
        if not self.keep_xml:
            logger.info(f"XML files deleted:   {stats['xml_deleted']}")
        logger.info("=" * 80)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Extract text content from Form 13F XML filings"
    )
    parser.add_argument(
        "--quarter",
        type=str,
        help="Specific quarter to process (e.g., '2024-Q4')"
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Maximum number of filings to process"
    )
    parser.add_argument(
        "--keep-xml",
        action="store_true",
        help="Keep XML files after processing (default: delete)"
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        default=True,
        help="Skip filings that already have text content (default: True)"
    )
    parser.add_argument(
        "--no-skip-existing",
        action="store_true",
        help="Process all filings, even if they already have text content"
    )

    args = parser.parse_args()

    # Get database URL
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logger.error("DATABASE_URL not found in environment")
        sys.exit(1)

    # Handle skip_existing flag
    skip_existing = args.skip_existing and not args.no_skip_existing

    # Initialize pipeline
    pipeline = TextExtractionPipeline(
        database_url=database_url,
        keep_xml=args.keep_xml
    )

    # Run pipeline
    try:
        stats = pipeline.run(
            quarter=args.quarter,
            limit=args.limit,
            skip_existing=skip_existing
        )

        # Exit with success if we inserted at least some sections
        if stats["sections_inserted"] > 0:
            logger.info("\nPipeline completed successfully!")
            sys.exit(0)
        else:
            logger.warning("\nPipeline completed but no sections were inserted")
            sys.exit(0)

    except KeyboardInterrupt:
        logger.info("\nPipeline interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\nPipeline failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
