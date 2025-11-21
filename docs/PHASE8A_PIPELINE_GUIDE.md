# Phase 8A: Text Extraction Pipeline Guide

## Overview

Phase 8A provides a complete automated pipeline for extracting text content from Form 13F XML filings. The pipeline downloads XMLs from SEC EDGAR, parses them, and stores extracted text in PostgreSQL.

## Components

### 1. Core Modules
- `src/ingestion/edgar_xml_downloader.py` - Downloads XML filings from SEC EDGAR
- `src/ingestion/xml_parser.py` - Parses XML and extracts text sections
- `schema/003_filing_text_content.sql` - Database schema for text storage

### 2. Scripts
- `scripts/extract_filing_text.py` - **Main pipeline script** (automated workflow)
- `scripts/check_text_coverage.py` - Analyze extraction coverage
- `scripts/test_phase8a.py` - Component testing

## Quick Start

### 1. Run the pipeline on a small sample

```bash
# Process 10 filings (test run)
python scripts/extract_filing_text.py --limit 10

# Process specific quarter
python scripts/extract_filing_text.py --quarter 2024-Q4

# Process all filings from 2024
python scripts/extract_filing_text.py --quarter 2024-Q1
python scripts/extract_filing_text.py --quarter 2024-Q2
python scripts/extract_filing_text.py --quarter 2024-Q3
python scripts/extract_filing_text.py --quarter 2024-Q4
```

### 2. Check extraction coverage

```bash
# Basic stats
python scripts/check_text_coverage.py

# Detailed breakdown
python scripts/check_text_coverage.py --detailed

# Show filings without text
python scripts/check_text_coverage.py --show-missing 50
```

### 3. Full historical ingestion

```bash
# Process ALL filings (will take ~2-3 hours for 8,000+ filings)
python scripts/extract_filing_text.py

# Process with progress monitoring
python scripts/extract_filing_text.py --limit 1000
python scripts/check_text_coverage.py --detailed
# Repeat until all done
```

## Pipeline Options

### extract_filing_text.py

```bash
# Basic usage
python scripts/extract_filing_text.py

# Options
--quarter QUARTER        # Process specific quarter (e.g., "2024-Q4")
--limit N               # Process only N filings
--keep-xml              # Keep XML files after processing (default: delete)
--skip-existing         # Skip filings with existing text (default: True)
--no-skip-existing      # Process all filings, even duplicates
```

### check_text_coverage.py

```bash
# Basic usage
python scripts/check_text_coverage.py

# Options
--detailed              # Show quarter and manager breakdowns
--show-missing N        # Show N filings without text content
```

## What Gets Extracted

The parser extracts these text sections from Form 13F-HR XML filings:

1. **cover_page_info** - Filing manager details, report info
2. **explanatory_notes** - Investment strategy, methodology explanations
3. **amendment_info** - Reasons for amendments (if applicable)
4. **other_documents** - Additional exhibits and documents

## Database Schema

Text content is stored in the `filing_text_content` table:

```sql
CREATE TABLE filing_text_content (
    id SERIAL PRIMARY KEY,
    accession_number VARCHAR(25) REFERENCES filings(accession_number),
    content_type VARCHAR(50),           -- Type of text section
    text_content TEXT,                  -- Extracted text
    xml_stored BOOLEAN,                 -- Whether XML is stored
    xml_storage_path TEXT,              -- Path to XML (if stored)
    extracted_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(accession_number, content_type)
);
```

View the enriched data:

```sql
-- Get all extracted text
SELECT * FROM filing_text_enriched;

-- Count by content type
SELECT content_type, COUNT(*)
FROM filing_text_content
GROUP BY content_type;

-- Find filings with explanatory notes
SELECT accession_number, manager_name, text_content
FROM filing_text_enriched
WHERE content_type = 'explanatory_notes';
```

## Storage Strategy

### Current Approach (Phase 8A)
- Download XML → Parse → Store text → **Delete XML**
- Only extracted text is stored in PostgreSQL
- Estimated storage: ~1-2 GB for all filings

### Optional (if needed later)
- Use `--keep-xml` flag to preserve XML files
- Store path in `xml_storage_path` column
- Set `xml_stored = true`

## Performance

### Download Speed
- SEC rate limit: 10 requests/second
- Actual speed: ~3-5 filings/second (with rate limiting)
- Total time for 8,000 filings: ~30-45 minutes

### Processing Speed
- Parsing: ~100-200 files/second
- Database insert: ~50-100 records/second
- Total pipeline: ~2-3 hours for full historical data

### Expected Results
- ~20-30% of filings will have meaningful text content
- Most filings only have cover page info
- Amendments and complex strategies have more text

## Monitoring Progress

### During execution
```bash
# Watch logs
python scripts/extract_filing_text.py --limit 100

# Check database in real-time
psql $DATABASE_URL -c "SELECT COUNT(*) FROM filing_text_content"
```

### After execution
```bash
# Get coverage stats
python scripts/check_text_coverage.py --detailed

# Query specific content types
psql $DATABASE_URL -c "
  SELECT content_type, COUNT(*) as count,
         AVG(LENGTH(text_content)) as avg_length
  FROM filing_text_content
  GROUP BY content_type
"
```

## Troubleshooting

### Issue: "Response is not XML"
**Cause:** SEC URL format changed or CIK formatting issue
**Fix:** Already handled in current version (uses Archives API)

### Issue: "Accession number is None"
**Cause:** Parser can't extract accession number
**Fix:** Already handled - extracts from filename

### Issue: Rate limited by SEC
**Cause:** Downloading too fast
**Fix:** Built-in rate limiting (110ms delay between requests)

### Issue: Database connection timeout
**Cause:** Too many connections or long-running query
**Fix:** Pipeline uses connection pooling, auto-reconnects

## Next Steps (Phase 8B)

After completing text extraction:

1. **Set up Qdrant** - Vector database for embeddings
2. **Create embeddings** - Use sentence-transformers
3. **Build RAG tool** - Retrieval-Augmented Generation
4. **Integrate with agent** - Add to orchestrator
5. **Update UI** - Show citations and sources

## Files Created

```
form13f_aiagent/
├── src/ingestion/
│   ├── edgar_xml_downloader.py      # XML downloader
│   └── xml_parser.py                # XML parser
├── schema/
│   └── 003_filing_text_content.sql  # Database schema
├── scripts/
│   ├── extract_filing_text.py       # Main pipeline script
│   ├── check_text_coverage.py       # Coverage analysis
│   └── test_phase8a.py              # Component tests
└── docs/
    └── PHASE8A_PIPELINE_GUIDE.md    # This guide
```

## Example Workflow

```bash
# 1. Test with small sample
python scripts/extract_filing_text.py --limit 10
python scripts/check_text_coverage.py

# 2. Process recent quarter
python scripts/extract_filing_text.py --quarter 2025-Q2
python scripts/check_text_coverage.py --detailed

# 3. Process all historical data
python scripts/extract_filing_text.py
python scripts/check_text_coverage.py --detailed

# 4. Verify results
psql $DATABASE_URL -c "SELECT * FROM filing_text_enriched LIMIT 10"
```

## Support

If you encounter issues:
1. Check logs for specific error messages
2. Run component tests: `python scripts/test_phase8a.py`
3. Verify database connection: `psql $DATABASE_URL`
4. Check SEC EDGAR status: https://www.sec.gov/edgar/searchedgar/companysearch.html
