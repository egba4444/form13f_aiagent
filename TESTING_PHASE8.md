# Phase 8A Testing - Quick Start Guide

## What We've Built So Far

✅ **SEC EDGAR XML Downloader** (`src/ingestion/edgar_xml_downloader.py`)
- Downloads 13F-HR XML filings from SEC
- Rate-limited (10 requests/second)
- Progress tracking
- Organized by year/quarter

✅ **XML Parser** (`src/ingestion/xml_parser.py`)
- Parses 13F-HR XML structure
- Extracts text sections:
  - Cover page information
  - Explanatory notes
  - Amendment information
  - Other documents

✅ **Database Schema** (`schema/003_filing_text_content.sql`)
- New table: `filing_text_content`
- Stores extracted text with metadata
- Indexes for fast retrieval
- Full-text search support

✅ **Test Suite** (`scripts/test_phase8a.py`)
- Tests all components end-to-end
- Downloads 5 sample filings
- Parses and inserts into database

## Quick Start - Run the Tests

### Step 1: Apply Database Migration

```bash
# Make sure you're in the project root directory
cd C:\Users\Hodol\Projects\form13f_aiagent

# Apply the migration
python scripts/apply_migration.py schema/003_filing_text_content.sql
```

Expected output:
```
Applying migration: 003_filing_text_content.sql
Database: aws-0-us-west-1.pooler.supabase.com
Executing 15 SQL statements...
✅ Migration applied successfully
```

### Step 2: Run the Test Suite

```bash
python scripts/test_phase8a.py
```

This will:
1. ✅ Verify database connection
2. ⬇️ Download 5 sample XML filings (~30 seconds)
3. 📄 Parse the XML files
4. 💾 Insert text into database

### Step 3: Verify Results

```bash
# Connect to your database
psql $DATABASE_URL

# Or using Python
python
>>> from sqlalchemy import create_engine, text
>>> import os
>>> engine = create_engine(os.getenv("DATABASE_URL"))
>>> with engine.connect() as conn:
...     result = conn.execute(text("SELECT COUNT(*) FROM filing_text_content"))
...     print(f"Text sections stored: {result.scalar()}")
```

Expected: 5-15 text sections (depending on which filings have text content)

## What the Tests Do

### Test 1: Database Connection
- Connects to PostgreSQL
- Verifies `filings` table exists (should have ~8,483 rows)
- Verifies `filing_text_content` table exists (should be empty initially)

### Test 2: XML Downloader
- Queries database for 5 recent filings
- Downloads XMLs from SEC EDGAR (respects rate limiting)
- Saves to `data/xml_filings_test/YYYY/QX/`
- Shows progress bar

### Test 3: XML Parser
- Reads each downloaded XML
- Extracts text sections
- Shows preview of extracted content
- Reports how many characters extracted

### Test 4: Database Insert
- Inserts parsed text into `filing_text_content` table
- Uses upsert (INSERT ... ON CONFLICT)
- Commits transaction
- Verifies data was stored

## Expected Test Results

**All Green:**
```
================================================================================
TEST SUMMARY
================================================================================
✅ PASS: Database
✅ PASS: Downloader
✅ PASS: Parser
✅ PASS: Insert

🎉 All tests passed! Phase 8A components are working.
```

## If Tests Fail

### ❌ Database test fails

**Error:** `relation "filing_text_content" does not exist`

**Fix:**
```bash
python scripts/apply_migration.py schema/003_filing_text_content.sql
```

### ❌ Downloader test fails

**Error:** `403 Forbidden` or `Connection timeout`

**Possible causes:**
1. SEC EDGAR may be temporarily down (check https://www.sec.gov/)
2. Rate limiting too aggressive (wait a bit and retry)
3. Network/firewall blocking SEC.gov

**Fix:**
- Wait a few minutes and retry
- Check your internet connection
- Verify SEC.gov is accessible in browser

### ❌ Parser test fails

**Error:** `No text sections found`

**This is normal!** Many 13F filings don't have explanatory text.
- Only amendments usually have text
- Cover page info is minimal
- Solution: Run more samples (increase limit to 20)

### ❌ Insert test fails

**Error:** `foreign key constraint`

**Cause:** Downloaded XMLs are for filings not in your `filings` table

**Fix:**
- Make sure your `filings` table is populated with data
- Run `python -m src.ingestion.ingest` first to load TSV data

## Next Steps After Testing

Once tests pass, you're ready to:

1. **Review the Downloaded Data**
   ```bash
   # Check what was downloaded
   ls -lh data/xml_filings_test/

   # View a sample XML
   cat data/xml_filings_test/2024/Q4/*.xml | head -100
   ```

2. **Query the Extracted Text**
   ```sql
   -- See all extracted text
   SELECT * FROM filing_text_enriched LIMIT 10;

   -- Find filings with explanatory notes
   SELECT
       manager_name,
       period_of_report,
       LENGTH(text_content) as text_length
   FROM filing_text_enriched
   WHERE content_type = 'explanatory_notes'
   ORDER BY text_length DESC;

   -- Test full-text search
   SELECT
       manager_name,
       content_type,
       LEFT(text_content, 200)
   FROM filing_text_enriched
   WHERE to_tsvector('english', text_content) @@ to_tsquery('english', 'Apple | Tesla')
   LIMIT 5;
   ```

3. **Run a Bigger Test** (optional)
   ```bash
   # Download 100 filings for Berkshire Hathaway
   python -m src.ingestion.edgar_xml_downloader \
       --manager-cik 0001067983 \
       --limit 100

   # This will take ~2 minutes (rate limiting)
   ```

4. **Continue Building Phase 8**
   - Create text extraction pipeline (combines downloader + parser + insert)
   - Run full historical ingestion (~2-3 hours for all filings)
   - Proceed to Phase 8B (Qdrant + RAG)

## File Locations

After testing, you'll have:

```
form13f_aiagent/
├── data/
│   └── xml_filings_test/        ← Downloaded XMLs (test data)
│       └── 2024/
│           └── Q4/
│               ├── 0001067983-25-000001.xml
│               └── ...
├── schema/
│   └── 003_filing_text_content.sql  ← Database schema
├── src/
│   └── ingestion/
│       ├── edgar_xml_downloader.py  ← XML downloader
│       └── xml_parser.py            ← XML parser
└── scripts/
    ├── apply_migration.py       ← Migration helper
    └── test_phase8a.py          ← Test suite
```

## Performance Notes

- **Download:** ~1 XML/second (SEC rate limit)
- **Parse:** ~100 XMLs/second (CPU-bound)
- **Insert:** ~50 inserts/second (database I/O)

**For 8,000 filings:**
- Download: ~2.2 hours
- Parse + Insert: ~5 minutes
- **Total:** ~2.5 hours

## Cleanup

To remove test data:

```bash
# Delete test XML files
rm -rf data/xml_filings_test/

# Delete test data from database
psql $DATABASE_URL -c "DELETE FROM filing_text_content;"
```

## Questions?

Check the detailed guide: `docs/PHASE8_TESTING.md`

Or run tests in verbose mode:
```bash
python scripts/test_phase8a.py --verbose
```
