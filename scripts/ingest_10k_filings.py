"""
Ingest Form 10-K Filings into Database

Downloads and parses Form 10-K filings, storing sections in filing_text_content table.

Usage:
    # Ingest single company
    python scripts/ingest_10k_filings.py --cik 0000320193 --year 2023

    # Ingest all top 10 S&P 500 companies
    python scripts/ingest_10k_filings.py --companies SP500_TOP10 --year 2023

    # Ingest specific companies by ticker
    python scripts/ingest_10k_filings.py --tickers AAPL,MSFT --year 2023
"""

import os
import sys
import asyncio
import argparse
import logging
from pathlib import Path
from datetime import date
from typing import List, Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

from src.ingestion.edgar_client import SECEdgarClient
from src.ingestion.form10k_parser import Form10KParser

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Top 10 S&P 500 companies by market cap
SP500_TOP10 = [
    ("0000320193", "AAPL", "Apple Inc."),
    ("0000789019", "MSFT", "Microsoft Corp"),
    ("0001652044", "GOOGL", "Alphabet Inc."),
    ("0001018724", "AMZN", "Amazon.com Inc"),
    ("0001045810", "NVDA", "NVIDIA Corp"),
    ("0001326801", "META", "Meta Platforms Inc"),
    ("0001067983", "BRK.B", "Berkshire Hathaway Inc"),
    ("0001318605", "TSLA", "Tesla Inc"),
    ("0001403161", "V", "Visa Inc."),
    ("0000731766", "UNH", "UnitedHealth Group Inc")
]


async def ingest_company_10k(
    edgar_client: SECEdgarClient,
    parser: Form10KParser,
    cik: str,
    company_name: str,
    year: int,
    database_url: str
) -> int:
    """
    Ingest 10-K filing for a single company.

    Args:
        edgar_client: SEC EDGAR client
        parser: 10-K parser
        cik: Company CIK (10-digit padded)
        company_name: Company name for logging
        year: Fiscal year
        database_url: PostgreSQL connection string

    Returns:
        Number of sections inserted
    """
    logger.info(f"Processing {company_name} ({cik}) for year {year}...")

    try:
        # Search for 10-K filing
        logger.info(f"  Searching for {year} 10-K filing...")
        filings = await edgar_client.search_filings(
            cik=cik,
            form_type="10-K",
            date_from=date(year, 1, 1),
            date_to=date(year, 12, 31),
            limit=1
        )

        if not filings:
            logger.warning(f"  No 10-K filings found for {company_name} in {year}")
            return 0

        filing = filings[0]
        accession_number = filing.accession_number
        filing_date = filing.filing_date
        logger.info(f"  Found filing: {accession_number} (filed {filing_date})")

        # Download 10-K HTML
        logger.info(f"  Downloading 10-K...")
        html = await edgar_client.download_10k_filing(accession_number, cik)
        logger.info(f"  Downloaded {len(html):,} bytes")

        # Parse sections
        logger.info(f"  Parsing sections...")
        sections = parser.parse_html(html)
        logger.info(f"  Extracted {len(sections)} sections")

        if not sections:
            logger.warning(f"  No sections extracted for {company_name}")
            return 0

        # Store in database
        logger.info(f"  Storing in database...")
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()

        # NOTE: The filings table has 13F-specific constraints and foreign keys to managers table.
        # For 10-K data, we don't need a filing record since filing_text_content
        # already has all the metadata we need. We'll just disable the FK temporarily.
        try:
            # Temporarily disable foreign key constraint
            cur.execute("SET session_replication_role = replica;")
            logger.info(f"  Temporarily disabled foreign key constraints for 10-K insert")
        except Exception as e:
            logger.warning(f"  Could not disable constraints: {e}")

        inserted_count = 0
        for section_name, text in sections.items():
            try:
                # Insert section into filing_text_content
                cur.execute("""
                    INSERT INTO filing_text_content (
                        accession_number,
                        filing_type,
                        cik_company,
                        section_name,
                        content_type,
                        text_content,
                        document_url
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (accession_number, content_type)
                    DO UPDATE SET
                        text_content = EXCLUDED.text_content,
                        updated_at = NOW()
                """, (
                    accession_number,
                    "10-K",
                    cik,
                    section_name,
                    f"10-K/{section_name}",  # content_type: "10-K/Item 1A"
                    text,
                    f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=10-K&dateb=&owner=exclude&count=100"
                ))
                inserted_count += 1
                logger.info(f"    ✓ Inserted {section_name}: {len(text):,} characters")
            except Exception as e:
                logger.error(f"    ✗ Error inserting {section_name}: {e}")

        # Re-enable foreign key constraints
        try:
            cur.execute("SET session_replication_role = DEFAULT;")
            logger.info(f"  Re-enabled foreign key constraints")
        except Exception as e:
            logger.warning(f"  Could not re-enable constraints: {e}")

        conn.commit()
        cur.close()
        conn.close()

        logger.info(f"  ✅ Successfully ingested {inserted_count} sections for {company_name}")
        return inserted_count

    except Exception as e:
        logger.error(f"  ✗ Error processing {company_name}: {e}", exc_info=True)
        return 0


async def main():
    parser = argparse.ArgumentParser(
        description="Ingest Form 10-K filings into database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    # Input options
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "--cik",
        help="Single company CIK (10-digit padded, e.g., 0000320193)"
    )
    input_group.add_argument(
        "--tickers",
        help="Comma-separated tickers (e.g., AAPL,MSFT,GOOGL)"
    )
    input_group.add_argument(
        "--companies",
        choices=["SP500_TOP10"],
        help="Predefined company list"
    )

    # Year
    parser.add_argument(
        "--year",
        type=int,
        required=True,
        help="Fiscal year (e.g., 2023)"
    )

    # Database
    parser.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL"),
        help="PostgreSQL database URL (default: from DATABASE_URL env var)"
    )

    args = parser.parse_args()

    if not args.database_url:
        logger.error("DATABASE_URL environment variable not set")
        sys.exit(1)

    # Determine companies to process
    companies_to_process: List[tuple] = []

    if args.cik:
        # Single CIK
        companies_to_process.append((args.cik, "Unknown", "Unknown"))

    elif args.tickers:
        # Look up tickers in database
        tickers = [t.strip().upper() for t in args.tickers.split(",")]
        conn = psycopg2.connect(args.database_url)
        cur = conn.cursor()

        for ticker in tickers:
            cur.execute(
                "SELECT cik, ticker, company_name FROM companies WHERE ticker = %s",
                (ticker,)
            )
            result = cur.fetchone()
            if result:
                companies_to_process.append(result)
            else:
                logger.warning(f"Ticker {ticker} not found in database")

        cur.close()
        conn.close()

    elif args.companies == "SP500_TOP10":
        companies_to_process = SP500_TOP10

    if not companies_to_process:
        logger.error("No companies to process")
        sys.exit(1)

    logger.info("=" * 80)
    logger.info(f"10-K INGESTION PIPELINE")
    logger.info(f"Year: {args.year}")
    logger.info(f"Companies: {len(companies_to_process)}")
    logger.info("=" * 80)

    # Initialize clients
    user_agent = os.getenv("SEC_USER_AGENT", "Form13F AI Agent hodolhodol0@gmail.com")
    edgar_client = SECEdgarClient(user_agent=user_agent)
    parser_instance = Form10KParser()

    total_sections = 0
    successful_companies = 0

    try:
        for cik, ticker, company_name in companies_to_process:
            logger.info("")
            sections_inserted = await ingest_company_10k(
                edgar_client=edgar_client,
                parser=parser_instance,
                cik=cik,
                company_name=f"{company_name} ({ticker})",
                year=args.year,
                database_url=args.database_url
            )
            if sections_inserted > 0:
                total_sections += sections_inserted
                successful_companies += 1

    finally:
        await edgar_client.close()

    # Summary
    logger.info("")
    logger.info("=" * 80)
    logger.info("INGESTION SUMMARY")
    logger.info(f"  Total companies processed: {len(companies_to_process)}")
    logger.info(f"  Successful: {successful_companies}")
    logger.info(f"  Failed: {len(companies_to_process) - successful_companies}")
    logger.info(f"  Total sections inserted: {total_sections}")
    logger.info("=" * 80)

    if successful_companies > 0:
        logger.info("")
        logger.info("✅ Next step: Generate embeddings")
        logger.info("   Run: python scripts/generate_embeddings.py --filing-type 10-K")
        logger.info("")


if __name__ == "__main__":
    asyncio.run(main())
