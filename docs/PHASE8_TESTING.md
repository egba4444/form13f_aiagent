# Phase 8 Testing Guide

## Prerequisites

Before testing Phase 8A components, ensure you have:

1. ✅ Database running and accessible
2. ✅ `.env` file configured with `DATABASE_URL`
3. ✅ Python dependencies installed

## Step 1: Apply Database Migration

First, create the `filing_text_content` table:

```bash
# Option A: Using psql command line
psql $DATABASE_URL < schema/003_filing_text_content.sql

# Option B: Using Python script (create this if needed)
python scripts/apply_migration.py schema/003_filing_text_content.sql
```

**Verify the table was created:**

```sql
-- Connect to your database and run:
SELECT COUNT(*) FROM filing_text_content;
-- Should return 0 (empty table)

-- Check the schema:
\d filing_text_content
```

## Step 2: Run Test Script

```bash
python scripts/test_phase8a.py
```

**What this does:**

1. **Test 1: Database Connection**
   - Verifies DATABASE_URL is configured
   - Checks `filings` table exists
   - Checks `filing_text_content` table exists

2. **Test 2: XML Downloader**
   - Downloads 5 sample 13F-HR XML filings from SEC EDGAR
   - Saves to `data/xml_filings_test/`
   - Shows download statistics

3. **Test 3: XML Parser**
   - Parses the 5 downloaded XMLs
   - Extracts text sections
   - Shows preview of extracted content

4. **Test 4: Database Insert**
   - Inserts parsed text into `filing_text_content` table
   - Verifies data was stored correctly

## Expected Output

```
================================================================================
PHASE 8A COMPONENT TESTING
================================================================================

============================================================
TEST 1: Database Connection
============================================================
✅ Connected to database
   Filings in database: 8483
✅ filing_text_content table exists
   Text sections already stored: 0

============================================================
TEST 2: XML Downloader
============================================================
Downloading 5 sample filings...
Downloading XMLs: 100%|████████████| 5/5 [00:06<00:00,  1.3s/filing]

✅ Downloaded 5 XML files
   Sample file: 0001067983-25-000001.xml
   Location: data/xml_filings_test/2024/Q4

============================================================
TEST 3: XML Parser
============================================================
Parsing file 1/5: 0001067983-25-000001.xml
  Accession: 0001067983-25-000001
  Sections found: 2
    - cover_page_info: 245 chars
      Preview: Filing Manager: Berkshire Hathaway Inc
Address: 3555 Farnam Street, Omaha, NE 68131...
    - explanatory_notes: 523 chars
      Preview: The following explains changes to our holdings...

[... more files ...]

✅ Successfully parsed 5 files

============================================================
TEST 4: Database Insert
============================================================
  ✅ Inserted: 0001067983-25-000001 - cover_page_info
  ✅ Inserted: 0001067983-25-000001 - explanatory_notes
  [... more inserts ...]

✅ Successfully inserted 10 text sections
   Total text sections in database: 10

================================================================================
TEST SUMMARY
================================================================================
✅ PASS: Database
✅ PASS: Downloader
✅ PASS: Parser
✅ PASS: Insert

🎉 All tests passed! Phase 8A components are working.

Next steps:
1. Review test data in database
2. Continue with text extraction pipeline
3. Proceed to Phase 8B (RAG system)
================================================================================
```

## Step 3: Verify Test Data

Query the database to see the inserted data:

```sql
-- View all extracted text sections
SELECT
    accession_number,
    content_type,
    LENGTH(text_content) as text_length,
    LEFT(text_content, 100) as preview
FROM filing_text_content
ORDER BY accession_number, content_type;

-- Use the enriched view
SELECT
    manager_name,
    period_of_report,
    content_type,
    LENGTH(text_content) as chars
FROM filing_text_enriched
ORDER BY manager_name;

-- Test full-text search
SELECT
    manager_name,
    content_type,
    ts_headline('english', text_content, to_tsquery('english', 'portfolio'))
FROM filing_text_enriched
WHERE to_tsvector('english', text_content) @@ to_tsquery('english', 'portfolio')
LIMIT 5;
```

## Step 4: Clean Up Test Data (Optional)

If you want to remove test data before running full ingestion:

```sql
-- Delete test data
DELETE FROM filing_text_content;

-- Or keep it and re-run tests (inserts will update existing rows)
```

```bash
# Delete test XML files
rm -rf data/xml_filings_test/
```

## Troubleshooting

### Problem: "filing_text_content table does not exist"

**Solution:** Run the migration first:
```bash
psql $DATABASE_URL < schema/003_filing_text_content.sql
```

### Problem: "Error downloading XML: 403 Forbidden"

**Solution:** SEC may be blocking requests. Check:
- User-Agent header is set correctly
- Rate limiting is working (10 requests/second max)
- SEC EDGAR is accessible (visit https://www.sec.gov/)

### Problem: "No text sections found"

**Reason:** Not all 13F filings have qualitative text. This is expected.
- Some filings only have the holdings table (structured data)
- Amendments are more likely to have explanatory text
- Try downloading more filings to find ones with text

### Problem: Parser fails with XML error

**Solution:** Some XMLs may have malformed structure. This is handled:
- Parser uses BeautifulSoup (lenient)
- Errors are logged, not fatal
- Continue with other files

## Next Steps After Testing

Once all tests pass:

1. **Review the code:**
   - Check `edgar_xml_downloader.py` - understand rate limiting
   - Check `xml_parser.py` - see what sections are extracted
   - Check `003_filing_text_content.sql` - understand schema

2. **Run a larger test:**
   ```bash
   # Download 100 filings for a specific manager
   python -m src.ingestion.edgar_xml_downloader \
       --manager-cik 0001067983 \
       --limit 100
   ```

3. **Continue building:**
   - Create text extraction pipeline (combines downloader + parser)
   - Run full historical ingestion
   - Proceed to Phase 8B (RAG system)

## Performance Expectations

- **Download speed:** ~1 filing/second (SEC rate limit)
- **Parse speed:** ~100 filings/second (local processing)
- **Insert speed:** ~50 inserts/second (database)

**Estimated time for full historical load:**
- 8,000 filings @ 1/second = ~2.2 hours (with rate limiting)
- Parsing + inserting: ~5 minutes
- **Total:** ~2.5 hours for complete historical data
