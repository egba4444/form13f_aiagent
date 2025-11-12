# Supabase Setup Guide

Complete guide for using Supabase as your PostgreSQL database for the Form 13F AI Agent.

## Why Supabase?

**Supabase = PostgreSQL + Extras**

✅ **Managed PostgreSQL** - No server maintenance
✅ **Free tier** - 500MB database, 2GB bandwidth
✅ **Automatic backups** - Point-in-time recovery
✅ **Dashboard UI** - Browse tables, run SQL queries
✅ **Realtime** - (optional) Subscribe to database changes
✅ **Auth & Storage** - (optional) Built-in authentication
✅ **Fast global network** - Low latency worldwide

## Quick Start (3 Steps)

### 1. Create Supabase Project

1. Go to https://supabase.com
2. Click **"New Project"**
3. Fill in:
   - **Name**: `form13f-aiagent` (or your choice)
   - **Database Password**: Create a strong password (save this!)
   - **Region**: Choose closest to you (e.g., `US West`, `EU Central`)
   - **Pricing Plan**: Free (or Pro if needed)
4. Click **"Create new project"**
5. Wait ~2 minutes for provisioning

### 2. Get Connection String

1. In your project dashboard, go to **Settings** (gear icon)
2. Click **Database** in left sidebar
3. Scroll to **Connection String** section
4. Select **URI** mode (not "Transaction" or "Session")
5. Copy the connection string (looks like):
   ```
   postgresql://postgres.abcdefghijklmnop:[YOUR-PASSWORD]@aws-0-us-west-1.pooler.supabase.com:5432/postgres
   ```
6. Replace `[YOUR-PASSWORD]` with your actual database password

### 3. Configure and Run

1. **Update `.env.supabase`**:
   ```bash
   DATABASE_URL=postgresql://postgres.xxxxx:your_password@aws-0-us-west-1.pooler.supabase.com:5432/postgres
   ```

2. **Switch to Supabase environment**:
   ```bash
   scripts\use-supabase.bat
   ```

3. **Create tables**:
   ```bash
   .venv\Scripts\python scripts/setup_database.py
   ```

4. **Load data**:
   ```bash
   .venv\Scripts\python -m src.ingestion.ingest
   ```

Done! 🎉

## Alternative: Create Schema via Dashboard

Instead of running the Python script, you can create tables manually via the Supabase dashboard:

### Method 1: SQL Editor (Recommended)

1. Go to **SQL Editor** in Supabase dashboard
2. Click **"New query"**
3. Copy the contents of `schema/001_initial_schema.sql`
4. Paste into the editor
5. Click **"Run"** (or press `Ctrl+Enter`)
6. Verify tables created in **Table Editor**

### Method 2: Table Editor UI

1. Go to **Table Editor** in Supabase dashboard
2. Click **"New table"**
3. Create each table manually:
   - **managers**: columns `cik`, `name`
   - **issuers**: columns `cusip`, `name`, `figi`
   - **filings**: columns `accession_number`, `cik`, `filing_date`, etc.
   - **holdings**: columns `id`, `accession_number`, `cusip`, etc.

**Note**: Method 1 (SQL Editor) is faster and includes all indexes/constraints.

## Verifying Setup

### Check Tables Exist

**Via SQL Editor:**
```sql
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public';
```

You should see:
- `filings`
- `holdings`
- `issuers`
- `managers`

### Check Row Counts

```sql
SELECT
  (SELECT COUNT(*) FROM managers) as managers,
  (SELECT COUNT(*) FROM issuers) as issuers,
  (SELECT COUNT(*) FROM filings) as filings,
  (SELECT COUNT(*) FROM holdings) as holdings;
```

Expected (after loading Q2 2025 data):
- **managers**: ~8,500
- **issuers**: ~14,000
- **filings**: ~8,500
- **holdings**: ~3,360,000

### View Sample Data

```sql
-- Top 10 managers by portfolio value
SELECT m.name, f.total_value
FROM filings f
JOIN managers m ON f.cik = m.cik
ORDER BY f.total_value DESC
LIMIT 10;

-- Top 10 holdings by value
SELECT i.name, h.value, h.shares_or_principal
FROM holdings h
JOIN issuers i ON h.cusip = i.cusip
ORDER BY h.value DESC
LIMIT 10;
```

## Using Supabase Features

### Table Editor

**Browse data visually:**
1. Go to **Table Editor**
2. Select a table (e.g., `holdings`)
3. View, filter, sort, and search rows
4. Click row to edit (be careful!)
5. Export to CSV if needed

**Useful for:**
- Quick data exploration
- Verifying data loaded correctly
- Exporting sample datasets

### SQL Editor

**Run ad-hoc queries:**
1. Go to **SQL Editor**
2. Write custom SQL queries
3. Save queries for later
4. Export results to CSV/JSON

**Example saved queries:**
- "Top Holdings by Value"
- "Manager Portfolio Size"
- "Berkshire Hathaway Holdings"

### Database Settings

**View connection info:**
- Go to **Settings** → **Database**
- **Connection pooling**: Enabled by default (good!)
- **Connection limit**: 60 (free tier)
- **Database size**: Monitor usage

**Important settings:**
- **Pooler**: Use pooler URL for applications (better performance)
- **Direct connection**: Only for migrations/admin tasks
- **IPv4 address**: If you need static IP

### Backups

**Automatic backups (Pro plan):**
- Point-in-time recovery
- Daily automated backups
- 7-day retention

**Free tier:**
- No automatic backups
- Manual export via **Database** → **Backups** → **Download**

**Recommended:**
1. Go to **Database** → **Backups**
2. Click **"Create backup"**
3. Download the `.sql` file
4. Store safely (e.g., Google Drive, GitHub private repo)

## Performance Tips

### Use Connection Pooling

Always use the **pooler** connection string (contains `pooler.supabase.com`), not the direct connection.

```bash
# ✅ Good (pooler)
postgresql://postgres.xxxxx:pass@aws-0-us-west-1.pooler.supabase.com:5432/postgres

# ❌ Avoid (direct)
postgresql://postgres.xxxxx:pass@db.xxxxx.supabase.co:5432/postgres
```

### Monitor Usage

1. Go to **Settings** → **Billing & Usage**
2. Check:
   - **Database size** (500MB limit on free tier)
   - **Bandwidth** (2GB/month on free tier)
   - **Active connections**

### Indexes

All necessary indexes are created by `schema/001_initial_schema.sql`.

**Verify indexes:**
```sql
SELECT indexname, tablename
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;
```

### Query Performance

**Use EXPLAIN to analyze slow queries:**
```sql
EXPLAIN ANALYZE
SELECT h.*, i.name
FROM holdings h
JOIN issuers i ON h.cusip = i.cusip
WHERE i.name LIKE '%APPLE%';
```

## Troubleshooting

### Connection Refused

**Problem**: `psycopg2.OperationalError: could not connect to server`

**Solutions**:
1. Check DATABASE_URL in `.env` is correct
2. Verify password doesn't contain special characters (if so, URL-encode it)
3. Check Supabase project is active (not paused)
4. Ensure you're using **pooler** URL, not direct connection

### Password with Special Characters

If your password contains `@`, `#`, `:`, etc., URL-encode it:

```python
from urllib.parse import quote_plus
password = "my@pass#123"
encoded = quote_plus(password)
print(encoded)  # "my%40pass%23123"
```

Then use in DATABASE_URL:
```bash
DATABASE_URL=postgresql://postgres.xxxxx:my%40pass%23123@...
```

### SSL Required

If you get SSL errors, add `?sslmode=require` to your DATABASE_URL:

```bash
DATABASE_URL=postgresql://...postgres?sslmode=require
```

### Project Paused (Free Tier)

Supabase pauses inactive projects after 7 days on the free tier.

**Solution**:
1. Go to Supabase dashboard
2. Click **"Resume project"**
3. Wait ~1 minute for reactivation

**Prevent pausing**: Upgrade to Pro plan ($25/month) or make a query every few days.

### Database Full

Free tier has 500MB limit.

**Check size:**
```sql
SELECT pg_size_pretty(pg_database_size('postgres')) AS database_size;
```

**Solutions**:
1. Delete old data (e.g., old quarters)
2. Upgrade to Pro plan (8GB included)
3. Use `VACUUM FULL` to reclaim space

### Slow Queries

**Problem**: Queries taking > 5 seconds

**Solutions**:
1. Check indexes exist: `\di` in psql
2. Use `EXPLAIN ANALYZE` to find bottlenecks
3. Add missing indexes
4. Upgrade to Pro plan (more resources)

## Switching Back to Docker

If you want to switch back to local Docker PostgreSQL:

```bash
# 1. Switch environment
scripts\use-docker.bat

# 2. Start Docker
docker compose up -d postgres

# 3. Create schema
.venv\Scripts\python scripts/setup_database.py

# 4. Load data
.venv\Scripts\python -m src.ingestion.ingest
```

## Cost Calculator

**Free Tier:**
- Database size: 500MB
- Bandwidth: 2GB/month
- No backups
- Projects pause after 7 days inactivity
- **Cost**: $0

**Pro Tier ($25/month):**
- Database size: 8GB
- Bandwidth: 50GB/month
- Daily backups (7-day retention)
- No auto-pause
- Custom domains
- **Cost**: $25/month

**For Form 13F:**
- Q2 2025 data: ~330MB (fits in free tier)
- 4 quarters/year: ~1.3GB (need Pro tier)

## Resources

- **Supabase Docs**: https://supabase.com/docs
- **SQL Editor**: https://supabase.com/docs/guides/database/sql-editor
- **Connection Pooling**: https://supabase.com/docs/guides/database/connecting-to-postgres#connection-pooling
- **Backups**: https://supabase.com/docs/guides/platform/backups
- **Pricing**: https://supabase.com/pricing

---

**Last Updated**: 2025-01-12
**Version**: 1.0
