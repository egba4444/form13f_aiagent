"""
Test script for Phase 8A components.

Tests:
1. Database connection
2. XML downloader (download 5 sample filings)
3. XML parser (parse downloaded files)
4. Database schema (insert test data)

Usage:
    python scripts/test_phase8a.py
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

load_dotenv()

from src.ingestion.edgar_xml_downloader import EdgarXMLDownloader
from src.ingestion.xml_parser import Form13FXMLParser
from sqlalchemy import create_engine, text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_database_connection():
    """Test 1: Verify database connection and schema."""
    logger.info("\n" + "="*60)
    logger.info("TEST 1: Database Connection")
    logger.info("="*60)

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logger.error("❌ DATABASE_URL not set")
        return False

    try:
        engine = create_engine(database_url)
        with engine.connect() as conn:
            # Check if filings table exists
            result = conn.execute(text("""
                SELECT COUNT(*) as count
                FROM filings
                LIMIT 1
            """))
            count = result.scalar()
            logger.info(f"✅ Connected to database")
            logger.info(f"   Filings in database: {count}")

            # Check if filing_text_content table exists
            try:
                result = conn.execute(text("""
                    SELECT COUNT(*) as count
                    FROM filing_text_content
                """))
                text_count = result.scalar()
                logger.info(f"✅ filing_text_content table exists")
                logger.info(f"   Text sections already stored: {text_count}")
            except Exception as e:
                logger.warning(f"⚠️  filing_text_content table may not exist yet")
                logger.warning(f"   Run: psql $DATABASE_URL < schema/003_filing_text_content.sql")
                return False

        return True

    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False


def test_xml_downloader():
    """Test 2: Download 5 sample XML filings."""
    logger.info("\n" + "="*60)
    logger.info("TEST 2: XML Downloader")
    logger.info("="*60)

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logger.error("❌ DATABASE_URL not set")
        return False

    try:
        # Create test output directory
        test_dir = Path("data/xml_filings_test")
        test_dir.mkdir(parents=True, exist_ok=True)

        # Initialize downloader
        downloader = EdgarXMLDownloader(
            database_url=database_url,
            output_dir=str(test_dir)
        )

        logger.info("Downloading 5 sample filings...")

        # Download just 5 filings for testing
        downloader.download_filings(
            limit=5,
            skip_existing=False
        )

        downloader.close()

        # Check results
        xml_files = list(test_dir.rglob("*.xml"))
        logger.info(f"\n✅ Downloaded {len(xml_files)} XML files")

        if xml_files:
            logger.info(f"   Sample file: {xml_files[0].name}")
            logger.info(f"   Location: {xml_files[0].parent}")
            return True, xml_files
        else:
            logger.error("❌ No XML files downloaded")
            return False, []

    except Exception as e:
        logger.error(f"❌ XML downloader failed: {e}", exc_info=True)
        return False, []


def test_xml_parser(xml_files):
    """Test 3: Parse downloaded XML files."""
    logger.info("\n" + "="*60)
    logger.info("TEST 3: XML Parser")
    logger.info("="*60)

    if not xml_files:
        logger.error("❌ No XML files to parse")
        return False, []

    parser = Form13FXMLParser()
    parsed_results = []

    for i, xml_file in enumerate(xml_files[:5], 1):
        logger.info(f"\nParsing file {i}/{len(xml_files[:5])}: {xml_file.name}")

        try:
            result = parser.parse_file(xml_file)

            logger.info(f"  Accession: {result['accession_number']}")
            logger.info(f"  Sections found: {len(result['sections'])}")

            if result['sections']:
                for section in result['sections']:
                    logger.info(f"    - {section['type']}: {len(section['text'])} chars")
                    logger.info(f"      Preview: {section['text'][:100]}...")
                parsed_results.append(result)
            else:
                logger.warning(f"  ⚠️  No text sections found")

        except Exception as e:
            logger.error(f"  ❌ Failed to parse: {e}")

    if parsed_results:
        logger.info(f"\n✅ Successfully parsed {len(parsed_results)} files")
        return True, parsed_results
    else:
        logger.error("\n❌ No files parsed successfully")
        return False, []


def test_database_insert(parsed_results):
    """Test 4: Insert parsed data into database."""
    logger.info("\n" + "="*60)
    logger.info("TEST 4: Database Insert")
    logger.info("="*60)

    if not parsed_results:
        logger.error("❌ No parsed results to insert")
        return False

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logger.error("❌ DATABASE_URL not set")
        return False

    try:
        engine = create_engine(database_url)
        inserted_count = 0

        with engine.connect() as conn:
            for result in parsed_results:
                accession_number = result['accession_number']
                if not accession_number:
                    logger.warning("⚠️  Skipping result with no accession number")
                    continue

                for section in result['sections']:
                    try:
                        # Insert text section
                        conn.execute(text("""
                            INSERT INTO filing_text_content
                            (accession_number, content_type, text_content, xml_stored, xml_storage_path)
                            VALUES (:accession, :content_type, :text, :xml_stored, :xml_path)
                            ON CONFLICT (accession_number, content_type)
                            DO UPDATE SET
                                text_content = EXCLUDED.text_content,
                                updated_at = NOW()
                        """), {
                            "accession": accession_number,
                            "content_type": section['type'],
                            "text": section['text'],
                            "xml_stored": True,
                            "xml_path": "data/xml_filings_test/"
                        })

                        inserted_count += 1
                        logger.info(f"  ✅ Inserted: {accession_number} - {section['type']}")

                    except Exception as e:
                        logger.error(f"  ❌ Failed to insert {accession_number}: {e}")

            conn.commit()

        logger.info(f"\n✅ Successfully inserted {inserted_count} text sections")

        # Verify
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT COUNT(*) FROM filing_text_content
            """))
            total = result.scalar()
            logger.info(f"   Total text sections in database: {total}")

        return True

    except Exception as e:
        logger.error(f"❌ Database insert failed: {e}", exc_info=True)
        return False


def main():
    """Run all tests."""
    logger.info("\n" + "="*80)
    logger.info("PHASE 8A COMPONENT TESTING")
    logger.info("="*80)

    results = {
        "database": False,
        "downloader": False,
        "parser": False,
        "insert": False
    }

    # Test 1: Database
    results["database"] = test_database_connection()
    if not results["database"]:
        logger.error("\n❌ Database test failed. Cannot continue.")
        logger.error("   Make sure to run: psql $DATABASE_URL < schema/003_filing_text_content.sql")
        return

    # Test 2: Downloader
    download_success, xml_files = test_xml_downloader()
    results["downloader"] = download_success

    if not results["downloader"]:
        logger.error("\n❌ Downloader test failed. Cannot continue.")
        return

    # Test 3: Parser
    parse_success, parsed_results = test_xml_parser(xml_files)
    results["parser"] = parse_success

    if not results["parser"]:
        logger.error("\n❌ Parser test failed. Cannot continue.")
        return

    # Test 4: Database Insert
    results["insert"] = test_database_insert(parsed_results)

    # Summary
    logger.info("\n" + "="*80)
    logger.info("TEST SUMMARY")
    logger.info("="*80)

    all_passed = all(results.values())

    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"{status}: {test_name.capitalize()}")

    if all_passed:
        logger.info("\n🎉 All tests passed! Phase 8A components are working.")
        logger.info("\nNext steps:")
        logger.info("1. Review test data in database")
        logger.info("2. Continue with text extraction pipeline")
        logger.info("3. Proceed to Phase 8B (RAG system)")
    else:
        logger.info("\n⚠️  Some tests failed. Please fix issues before continuing.")

    logger.info("="*80)


if __name__ == "__main__":
    main()
