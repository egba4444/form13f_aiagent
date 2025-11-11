# Form 13F Data Files

Place your Form 13F XML files in this directory.

## File Format

- **Format**: XML files
- **Naming**: Any naming convention (e.g., `ACCESSION_NUMBER.xml`, `CIK_YYYYMMDD.xml`)
- **Source**: SEC EDGAR Form 13F filings

## Example

```
data/raw/
├── 0001193125-23-123456.xml
├── 0001193125-23-234567.xml
└── 0001193125-23-345678.xml
```

## How to Ingest

After adding XML files here, run the ingestion command:

```bash
# Using Docker
docker-compose exec api python -m src.ingestion.ingest --folder /app/data/raw

# Or locally
python -m src.ingestion.ingest --folder ./data/raw
```

## Where to Find 13F Forms

1. Go to [SEC EDGAR](https://www.sec.gov/edgar/searchedgar/companysearch.html)
2. Search for an institutional investor (e.g., "Berkshire Hathaway")
3. Filter for "13F-HR" filings
4. Download the XML version of the filing
5. Place in this directory

## Notes

- XML files in this folder are tracked by git (committed to the repository)
- Processed data goes to `data/processed/` (not tracked by git)
- Cache files go to `data/cache/` (not tracked by git)
