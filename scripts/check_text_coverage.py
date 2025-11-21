"""
Check Text Coverage - Analyze which filings have extracted text

This script helps you understand:
- How many filings have text content extracted
- Which quarters/years have the most coverage
- Which managers have the most text content
- Overall text extraction statistics

Usage:
    # Check overall coverage
    python scripts/check_text_coverage.py

    # Check specific quarter
    python scripts/check_text_coverage.py --quarter 2024-Q4

    # Show detailed breakdown
    python scripts/check_text_coverage.py --detailed

    # Export to CSV
    python scripts/check_text_coverage.py --export coverage_report.csv
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

import psycopg2
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


class TextCoverageAnalyzer:
    """Analyzes text extraction coverage across filings."""

    def __init__(self, database_url: str):
        """Initialize analyzer."""
        self.database_url = database_url

    def get_overall_stats(self) -> Dict:
        """Get overall coverage statistics."""
        conn = psycopg2.connect(self.database_url)
        cur = conn.cursor()

        # Total filings
        cur.execute("SELECT COUNT(*) FROM filings")
        total_filings = cur.fetchone()[0]

        # Filings with text content
        cur.execute("""
            SELECT COUNT(DISTINCT accession_number)
            FROM filing_text_content
        """)
        filings_with_text = cur.fetchone()[0]

        # Total text sections
        cur.execute("SELECT COUNT(*) FROM filing_text_content")
        total_sections = cur.fetchone()[0]

        # Text sections by type
        cur.execute("""
            SELECT content_type, COUNT(*) as count
            FROM filing_text_content
            GROUP BY content_type
            ORDER BY count DESC
        """)
        sections_by_type = dict(cur.fetchall())

        # Average sections per filing
        avg_sections = total_sections / filings_with_text if filings_with_text > 0 else 0

        # Total text size
        cur.execute("""
            SELECT
                SUM(LENGTH(text_content)) as total_chars,
                AVG(LENGTH(text_content)) as avg_chars
            FROM filing_text_content
        """)
        total_chars, avg_chars = cur.fetchone()

        cur.close()
        conn.close()

        return {
            "total_filings": total_filings,
            "filings_with_text": filings_with_text,
            "coverage_percent": (filings_with_text / total_filings * 100) if total_filings > 0 else 0,
            "total_sections": total_sections,
            "avg_sections_per_filing": avg_sections,
            "sections_by_type": sections_by_type,
            "total_chars": total_chars or 0,
            "avg_chars": avg_chars or 0
        }

    def get_coverage_by_quarter(self) -> List[Dict]:
        """Get coverage statistics by quarter."""
        conn = psycopg2.connect(self.database_url)
        cur = conn.cursor()

        cur.execute("""
            SELECT
                EXTRACT(YEAR FROM period_of_report) as year,
                EXTRACT(QUARTER FROM period_of_report) as quarter,
                COUNT(*) as total_filings,
                COUNT(DISTINCT ftc.accession_number) as filings_with_text,
                ROUND(
                    COUNT(DISTINCT ftc.accession_number)::numeric / COUNT(*)::numeric * 100,
                    2
                ) as coverage_percent
            FROM filings f
            LEFT JOIN filing_text_content ftc ON f.accession_number = ftc.accession_number
            GROUP BY year, quarter
            ORDER BY year DESC, quarter DESC
            LIMIT 20
        """)

        results = []
        for row in cur.fetchall():
            year, quarter, total, with_text, coverage = row
            results.append({
                "quarter": f"{int(year)}-Q{int(quarter)}",
                "total_filings": total,
                "filings_with_text": with_text or 0,
                "coverage_percent": float(coverage) if coverage else 0
            })

        cur.close()
        conn.close()

        return results

    def get_top_managers_with_text(self, limit: int = 10) -> List[Dict]:
        """Get managers with most text content."""
        conn = psycopg2.connect(self.database_url)
        cur = conn.cursor()

        cur.execute("""
            SELECT
                m.name,
                m.cik,
                COUNT(DISTINCT ftc.accession_number) as filings_with_text,
                COUNT(ftc.id) as total_sections,
                SUM(LENGTH(ftc.text_content)) as total_chars
            FROM managers m
            JOIN filings f ON m.cik = f.cik
            JOIN filing_text_content ftc ON f.accession_number = ftc.accession_number
            GROUP BY m.name, m.cik
            ORDER BY total_sections DESC
            LIMIT %s
        """, (limit,))

        results = []
        for row in cur.fetchall():
            name, cik, filings, sections, chars = row
            results.append({
                "manager_name": name,
                "cik": cik,
                "filings_with_text": filings,
                "total_sections": sections,
                "total_chars": chars
            })

        cur.close()
        conn.close()

        return results

    def get_filings_without_text(self, limit: int = 100) -> List[Dict]:
        """Get filings that don't have text content yet."""
        conn = psycopg2.connect(self.database_url)
        cur = conn.cursor()

        cur.execute("""
            SELECT
                f.accession_number,
                f.cik,
                m.name,
                f.period_of_report,
                f.submission_type
            FROM filings f
            JOIN managers m ON f.cik = m.cik
            LEFT JOIN filing_text_content ftc ON f.accession_number = ftc.accession_number
            WHERE ftc.id IS NULL
            ORDER BY f.period_of_report DESC
            LIMIT %s
        """, (limit,))

        results = []
        for row in cur.fetchall():
            accession, cik, manager, period, form_type = row
            results.append({
                "accession_number": accession,
                "cik": cik,
                "manager_name": manager,
                "period_of_report": period.strftime("%Y-%m-%d"),
                "form_type": form_type
            })

        cur.close()
        conn.close()

        return results


def print_overall_stats(stats: Dict):
    """Print overall statistics."""
    print("\n" + "=" * 80)
    print("OVERALL TEXT EXTRACTION COVERAGE")
    print("=" * 80)
    print(f"Total filings:              {stats['total_filings']:,}")
    print(f"Filings with text content:  {stats['filings_with_text']:,}")
    print(f"Coverage:                   {stats['coverage_percent']:.2f}%")
    print(f"\nTotal text sections:        {stats['total_sections']:,}")
    print(f"Avg sections per filing:    {stats['avg_sections_per_filing']:.2f}")
    print(f"\nTotal characters:           {stats['total_chars']:,}")
    print(f"Avg characters per section: {stats['avg_chars']:.0f}")

    print("\nSections by type:")
    for content_type, count in stats['sections_by_type'].items():
        print(f"  - {content_type:25s} {count:>6,}")
    print("=" * 80)


def print_coverage_by_quarter(coverage: List[Dict]):
    """Print coverage by quarter."""
    print("\n" + "=" * 80)
    print("COVERAGE BY QUARTER")
    print("=" * 80)
    print(f"{'Quarter':<12} {'Total':<10} {'With Text':<12} {'Coverage':<10}")
    print("-" * 80)

    for item in coverage:
        print(
            f"{item['quarter']:<12} "
            f"{item['total_filings']:<10,} "
            f"{item['filings_with_text']:<12,} "
            f"{item['coverage_percent']:.1f}%"
        )
    print("=" * 80)


def print_top_managers(managers: List[Dict]):
    """Print top managers with text content."""
    print("\n" + "=" * 80)
    print("TOP MANAGERS WITH TEXT CONTENT")
    print("=" * 80)
    print(f"{'Manager Name':<40} {'Filings':<10} {'Sections':<10} {'Chars':<12}")
    print("-" * 80)

    for manager in managers:
        name = manager['manager_name'][:38]
        print(
            f"{name:<40} "
            f"{manager['filings_with_text']:<10} "
            f"{manager['total_sections']:<10} "
            f"{manager['total_chars']:<12,}"
        )
    print("=" * 80)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Analyze text extraction coverage"
    )
    parser.add_argument(
        "--detailed",
        action="store_true",
        help="Show detailed breakdown by quarter and manager"
    )
    parser.add_argument(
        "--show-missing",
        type=int,
        metavar="N",
        help="Show N filings without text content"
    )

    args = parser.parse_args()

    # Get database URL
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logger.error("DATABASE_URL not found in environment")
        sys.exit(1)

    # Initialize analyzer
    analyzer = TextCoverageAnalyzer(database_url)

    try:
        # Get and print overall stats
        logger.info("Fetching coverage statistics...")
        stats = analyzer.get_overall_stats()
        print_overall_stats(stats)

        # Detailed breakdown
        if args.detailed:
            coverage = analyzer.get_coverage_by_quarter()
            print_coverage_by_quarter(coverage)

            managers = analyzer.get_top_managers_with_text(limit=15)
            print_top_managers(managers)

        # Show filings without text
        if args.show_missing:
            logger.info(f"\nFetching {args.show_missing} filings without text content...")
            missing = analyzer.get_filings_without_text(limit=args.show_missing)

            print("\n" + "=" * 80)
            print(f"FILINGS WITHOUT TEXT CONTENT (showing {len(missing)})")
            print("=" * 80)

            for item in missing[:20]:  # Show first 20
                print(
                    f"{item['accession_number']} | "
                    f"{item['period_of_report']} | "
                    f"{item['manager_name'][:40]}"
                )

            if len(missing) > 20:
                print(f"\n... and {len(missing) - 20} more")
            print("=" * 80)

    except Exception as e:
        logger.error(f"Error analyzing coverage: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
