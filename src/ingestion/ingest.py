"""CLI tool for ingesting Form 13F data."""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from .tsv_parser import Form13FTSVParser


def main():
    """Main entry point for ingestion CLI."""
    parser = argparse.ArgumentParser(
        description="Ingest Form 13F TSV data from SEC bulk downloads"
    )
    parser.add_argument(
        "--folder",
        type=Path,
        required=True,
        help="Path to folder containing TSV files (SUBMISSION.tsv, INFOTABLE.tsv, etc.)",
    )
    parser.add_argument(
        "--stats-only",
        action="store_true",
        help="Only show statistics, don't parse all data",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional: Save parsed data to JSON file",
    )
    parser.add_argument(
        "--accession",
        type=str,
        help="Optional: Parse only a specific filing by accession number",
    )

    args = parser.parse_args()

    # Validate folder exists
    if not args.folder.exists():
        print(f"Error: Folder not found: {args.folder}", file=sys.stderr)
        sys.exit(1)

    try:
        # Initialize parser
        print(f"Loading Form 13F data from: {args.folder}")
        tsv_parser = Form13FTSVParser(args.folder)

        # Show statistics
        print("\n" + "=" * 60)
        print("DATA STATISTICS")
        print("=" * 60)
        stats = tsv_parser.get_stats()
        for key, value in stats.items():
            print(f"{key.replace('_', ' ').title()}: {value:,}")
        print("=" * 60)

        if args.stats_only:
            print("\nStats-only mode: Skipping full parse")
            return

        # Parse specific filing or all filings
        if args.accession:
            print(f"\nParsing filing: {args.accession}")
            parsed_filing = tsv_parser.parse_filing(args.accession)

            if not parsed_filing:
                print(f"Error: Filing {args.accession} not found", file=sys.stderr)
                sys.exit(1)

            print(f"\nFiling: {parsed_filing.metadata.manager_name}")
            print(f"CIK: {parsed_filing.metadata.cik}")
            print(f"Period: {parsed_filing.metadata.period_of_report}")
            print(f"Total Value: ${parsed_filing.metadata.total_value_millions:.2f}M")
            print(f"Holdings: {len(parsed_filing.holdings):,}")

            if parsed_filing.holdings:
                print("\nTop 5 Holdings:")
                top_holdings = sorted(
                    parsed_filing.holdings,
                    key=lambda h: h.value,
                    reverse=True
                )[:5]

                for i, holding in enumerate(top_holdings, 1):
                    print(
                        f"  {i}. {holding.issuer_name} "
                        f"(${holding.value_millions:.2f}M, "
                        f"{holding.shares_or_principal:,} {holding.sh_or_prn})"
                    )

            if args.output:
                output_data = {
                    "metadata": parsed_filing.metadata.model_dump(mode='json'),
                    "holdings": [h.model_dump(mode='json') for h in parsed_filing.holdings],
                }
                with open(args.output, 'w') as f:
                    json.dump(output_data, f, indent=2, default=str)
                print(f"\nSaved to: {args.output}")

        else:
            print("\nParsing all filings...")
            parsed_filings = tsv_parser.parse_all_filings()

            print(f"\nSuccessfully parsed {len(parsed_filings):,} filings")

            # Show top 10 managers by portfolio value
            print("\nTop 10 Managers by Portfolio Value:")
            top_managers = sorted(
                parsed_filings,
                key=lambda f: f.metadata.total_value,
                reverse=True
            )[:10]

            for i, filing in enumerate(top_managers, 1):
                print(
                    f"  {i}. {filing.metadata.manager_name[:50]:<50} "
                    f"${filing.metadata.total_value_millions:>12,.2f}M "
                    f"({filing.metadata.number_of_holdings:>5,} holdings)"
                )

            if args.output:
                output_data = []
                for filing in parsed_filings:
                    output_data.append({
                        "metadata": filing.metadata.model_dump(mode='json'),
                        "holdings": [h.model_dump(mode='json') for h in filing.holdings],
                    })

                with open(args.output, 'w') as f:
                    json.dump(output_data, f, indent=2, default=str)
                print(f"\nSaved {len(output_data):,} filings to: {args.output}")

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
