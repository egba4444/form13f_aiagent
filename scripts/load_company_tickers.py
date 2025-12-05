"""
Load SEC Company Tickers into Database

Downloads SEC's company_tickers.json and populates the companies table.

Source: https://www.sec.gov/files/company_tickers.json

Format:
{
  "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
  "1": {"cik_str": 789019, "ticker": "MSFT", "title": "MICROSOFT CORP"},
  ...
}

Usage:
    python scripts/load_company_tickers.py
    python scripts/load_company_tickers.py --mark-sp500  # Mark top 10 as S&P 500
"""

import os
import sys
import logging
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import requests
from psycopg2.extras import execute_values
from dotenv import load_dotenv
import psycopg2

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# SEC endpoint
SEC_COMPANY_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_USER_AGENT = os.getenv("SEC_USER_AGENT", "Form13F AI Agent hodolhodol0@gmail.com")

# Top 10 S&P 500 companies by market cap (as of 2024)
TOP_10_SP500 = [
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


def download_company_tickers():
    """Download company tickers JSON from SEC."""
    logger.info(f"Downloading company tickers from {SEC_COMPANY_TICKERS_URL}")

    headers = {
        "User-Agent": SEC_USER_AGENT,
        "Accept-Encoding": "gzip, deflate",
        "Host": "www.sec.gov"
    }

    response = requests.get(SEC_COMPANY_TICKERS_URL, headers=headers)
    response.raise_for_status()

    data = response.json()
    logger.info(f"Downloaded {len(data)} company records")

    return data


def load_to_database(data, database_url):
    """Load company tickers into database."""
    logger.info("Connecting to database...")
    conn = psycopg2.connect(database_url)
    cur = conn.cursor()

    try:
        # Prepare records and deduplicate by CIK (keep first occurrence)
        records = []
        seen_ciks = set()
        duplicates = 0

        for entry in data.values():
            cik = str(entry['cik_str']).zfill(10)  # Pad to 10 digits

            # Skip duplicates
            if cik in seen_ciks:
                duplicates += 1
                continue

            seen_ciks.add(cik)
            ticker = entry['ticker']
            name = entry['title']

            records.append((cik, ticker, name))

        logger.info(f"Inserting {len(records)} companies into database (skipped {duplicates} duplicates)...")

        # Bulk insert with conflict handling
        insert_query = """
            INSERT INTO companies (cik, ticker, company_name)
            VALUES %s
            ON CONFLICT (cik) DO UPDATE SET
                ticker = EXCLUDED.ticker,
                company_name = EXCLUDED.company_name,
                updated_at = NOW()
        """

        execute_values(cur, insert_query, records, page_size=1000)
        conn.commit()

        logger.info(f"✅ Successfully loaded {len(records)} companies")

        # Show stats
        cur.execute("SELECT COUNT(*) FROM companies")
        total = cur.fetchone()[0]
        logger.info(f"Total companies in database: {total}")

    except Exception as e:
        conn.rollback()
        logger.error(f"Error loading data: {e}")
        raise
    finally:
        cur.close()
        conn.close()


def mark_sp500_companies(database_url):
    """Mark top 10 S&P 500 companies in database."""
    logger.info("Marking top 10 S&P 500 companies...")

    conn = psycopg2.connect(database_url)
    cur = conn.cursor()

    try:
        for cik, ticker, name in TOP_10_SP500:
            cur.execute("""
                UPDATE companies
                SET is_sp500 = TRUE,
                    updated_at = NOW()
                WHERE cik = %s
            """, (cik,))

            if cur.rowcount > 0:
                logger.info(f"  ✅ Marked {ticker} ({name}) as S&P 500")
            else:
                logger.warning(f"  ⚠️  CIK {cik} ({ticker}) not found in database")

        conn.commit()

        # Verify
        cur.execute("SELECT COUNT(*) FROM companies WHERE is_sp500 = TRUE")
        sp500_count = cur.fetchone()[0]
        logger.info(f"Total S&P 500 companies marked: {sp500_count}")

    except Exception as e:
        conn.rollback()
        logger.error(f"Error marking S&P 500: {e}")
        raise
    finally:
        cur.close()
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Load SEC company tickers into database")
    parser.add_argument(
        "--mark-sp500",
        action="store_true",
        help="Mark top 10 S&P 500 companies after loading"
    )
    parser.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL"),
        help="PostgreSQL database URL (default: from DATABASE_URL env var)"
    )

    args = parser.parse_args()

    if not args.database_url:
        logger.error("DATABASE_URL environment variable not set")
        sys.exit(1)

    try:
        # Download data
        data = download_company_tickers()

        # Load to database
        load_to_database(data, args.database_url)

        # Mark S&P 500 if requested
        if args.mark_sp500:
            mark_sp500_companies(args.database_url)

        logger.info("=" * 60)
        logger.info("✅ Company tickers loaded successfully!")
        logger.info("=" * 60)
        logger.info("Next steps:")
        logger.info("1. Run: python scripts/ingest_10k_filings.py --cik 0000320193 --year 2023")
        logger.info("2. Run: python scripts/generate_embeddings.py --clear-first")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Failed to load company tickers: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
