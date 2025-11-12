# Form 13F Data Files

This directory contains Form 13F bulk data from the SEC in TSV format.

## File Format

The data is provided in tab-separated value (TSV) files:

### Core Files

- **SUBMISSION.tsv** - Filing metadata (accession number, CIK, filing date, period of report)
- **COVERPAGE.tsv** - Filing manager details (name, address, report type)
- **INFOTABLE.tsv** - Holdings data (CUSIP, issuer name, value, shares, voting authority)
- **SUMMARYPAGE.tsv** - Summary statistics (total entries, total value)
- **SIGNATURE.tsv** - Signatory information
- **OTHERMANAGER.tsv** - Other managers included in filing
- **OTHERMANAGER2.tsv** - Additional other manager data
- **FORM13F_metadata.json** - Complete schema definition
- **FORM13F_readme.htm** - SEC documentation

## Current Data

```
Period: Q2 2025 (01-JUN-2025 to 31-AUG-2025)
Files: 9 TSV/JSON/HTM files
```

## How to Ingest

After adding data files here, run the ingestion command:

```bash
# Using Docker
docker-compose exec api python -m src.ingestion.ingest --folder /app/data/raw

# Or locally
python -m src.ingestion.ingest --folder ./data/raw
```

## Where to Get Data

SEC provides quarterly bulk data downloads:

1. Go to [SEC Financial Statement Data Sets](https://www.sec.gov/dera/data/form-13f-data-sets)
2. Download the quarterly ZIP file (e.g., `01JUN2025-31AUG2025_form13f.zip`)
3. Extract and place TSV files in this directory

## Data Schema

The metadata file (`FORM13F_metadata.json`) contains complete schema definitions for all TSV files.

### Key Fields in INFOTABLE.tsv

- `ACCESSION_NUMBER` - Links to SUBMISSION.tsv
- `CUSIP` - Security identifier
- `NAMEOFISSUER` - Company name
- `VALUE` - Market value in dollars (not thousands!)
- `SSHPRNAMT` - Number of shares or principal amount
- `INVESTMENTDISCRETION` - SOLE, SHARED, or DEFINED
- `VOTING_AUTH_SOLE/SHARED/NONE` - Voting authority breakdown

## Notes

- TSV files in this folder are tracked by git (committed to the repository)
- Processed data goes to `data/processed/` (not tracked by git)
- Cache files go to `data/cache/` (not tracked by git)
- Data format changed from XML to TSV bulk format (easier to parse!)
