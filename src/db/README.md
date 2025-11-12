# Database Module

PostgreSQL database layer for Form 13F data.

## Schema

### Tables

1. **managers** - Institutional managers (filers)
   - Primary key: `cik` (10-digit CIK)
   - Columns: `name`

2. **issuers** - Security issuers (companies)
   - Primary key: `cusip` (9-character)
   - Columns: `name`, `figi` (optional)

3. **filings** - Form 13F filing metadata
   - Primary key: `accession_number`
   - Foreign key: `cik` → `managers.cik`
   - Columns: `filing_date`, `period_of_report`, `submission_type`, `report_type`, `total_value`, `number_of_holdings`

4. **holdings** - Individual security positions
   - Primary key: `id` (auto-increment)
   - Foreign keys: `accession_number` → `filings`, `cusip` → `issuers`
   - Columns: `title_of_class`, `value`, `shares_or_principal`, `sh_or_prn`, `investment_discretion`, `put_call`, `voting_authority_*`

### Relationships

```
managers (1) ──< (N) filings (1) ──< (N) holdings (N) >── (1) issuers
```

### Indexes

**Performance indexes for common queries:**
- `ix_filings_cik_period` - Manager holdings over time
- `ix_filings_period_value` - Top managers by period
- `ix_holdings_cusip_value` - Top holders of a security
- `ix_holdings_value_desc` - Largest positions overall
- `ix_holdings_accession_cusip` - Holdings within a filing

## Usage

### Running Migrations

```bash
# Start PostgreSQL
docker compose up -d postgres

# Run migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Show current version
alembic current
```

### Loading Data

```bash
# Load from TSV files
python -m src.db.loader data/raw

# Or use the loader in code
from src.db.loader import Form13FDatabaseLoader

with Form13FDatabaseLoader() as loader:
    stats = loader.load_from_tsv_folder("data/raw")
    print(f"Loaded {stats['holdings']:,} holdings")
```

### Querying Data

```python
from src.db import SessionLocal, Filing, Holding, Manager, Issuer
from sqlalchemy import select, func

# Get a session
with SessionLocal() as session:
    # Find Berkshire Hathaway
    stmt = select(Manager).where(Manager.name.like('%BERKSHIRE%'))
    berkshire = session.execute(stmt).scalar_one()

    # Get their latest filing
    stmt = (
        select(Filing)
        .where(Filing.cik == berkshire.cik)
        .order_by(Filing.period_of_report.desc())
        .limit(1)
    )
    latest_filing = session.execute(stmt).scalar_one()

    # Get top 10 holdings by value
    stmt = (
        select(Holding, Issuer)
        .join(Issuer)
        .where(Holding.accession_number == latest_filing.accession_number)
        .order_by(Holding.value.desc())
        .limit(10)
    )
    top_holdings = session.execute(stmt).all()

    for holding, issuer in top_holdings:
        print(f"{issuer.name}: ${holding.value:,}")
```

## Performance Tips

1. **Use bulk operations** - The loader uses `bulk_insert_mappings` for speed
2. **Batch large inserts** - Holdings are inserted in 5,000-row batches
3. **Leverage indexes** - All common query patterns are indexed
4. **Use upserts** - Managers and issuers use `ON CONFLICT DO UPDATE`
5. **Connection pooling** - Configured in `session.py` (pool_size=5)

## Database Configuration

Set via environment variables in `.env`:

```bash
DATABASE_URL=postgresql://form13f_user:your_password@localhost:5432/form13f
```

For Docker:
```bash
DB_PASSWORD=your_password  # Used in docker-compose.yml
```
