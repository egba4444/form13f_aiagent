# Database Schema

This directory contains SQL schema files for the Form 13F database.

## Files

- `001_initial_schema.sql` - Initial database schema with all tables and indexes

## Schema Overview

The database has 4 main tables:

```
managers (CIK, name)
    ↓
filings (accession_number, cik, filing_date, period_of_report, total_value, ...)
    ↓
holdings (id, accession_number, cusip, value, shares, voting_authority, ...)
    ↓
issuers (cusip, name, figi)
```

## Setup Instructions

### Option 1: Docker (Local Development)

1. **Start PostgreSQL**:
   ```bash
   docker compose up -d postgres
   ```

2. **Apply schema**:
   ```bash
   # Using psql
   psql -h localhost -p 5432 -U form13f_user -d form13f -f schema/001_initial_schema.sql

   # Or using Docker
   docker compose exec postgres psql -U form13f_user -d form13f -f /schema/001_initial_schema.sql
   ```

3. **Verify tables created**:
   ```bash
   psql -h localhost -p 5432 -U form13f_user -d form13f -c "\dt"
   ```

### Option 2: Supabase (Cloud)

1. **Go to Supabase Dashboard**: https://supabase.com/dashboard

2. **Navigate to SQL Editor**: Your Project → SQL Editor

3. **Copy and paste** the contents of `schema/001_initial_schema.sql`

4. **Click "Run"** to execute

5. **Verify** in Table Editor that tables were created

### Option 3: Python Script

```bash
# Run the setup script
python scripts/setup_database.py
```

## Using the Schema

### Check if schema exists

```sql
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public';
```

### Drop all tables (if you need to reset)

```sql
DROP TABLE IF EXISTS holdings CASCADE;
DROP TABLE IF EXISTS filings CASCADE;
DROP TABLE IF EXISTS issuers CASCADE;
DROP TABLE IF EXISTS managers CASCADE;
```

### View table structure

```sql
\d+ managers
\d+ issuers
\d+ filings
\d+ holdings
```

## Schema Changes

If you need to modify the schema:

1. **Create a new SQL file**: `002_your_change.sql`
2. **Document the change** in this README
3. **Apply it** to both Docker and Supabase
4. **Update** `src/db/models.py` SQLAlchemy models if needed

## Example Queries

See helpful comments at the bottom of `001_initial_schema.sql` for common query patterns.
