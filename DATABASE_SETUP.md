# Database Setup Guide

This project supports both **Docker (local)** and **Supabase (cloud)** PostgreSQL.

## Quick Start

### Option 1: Docker (Local Development)

**Best for:** Fast local testing, offline development, isolated environment

```bash
# 1. Switch to Docker environment
scripts\use-docker.bat

# 2. Start PostgreSQL container
docker compose up -d postgres

# 3. Create tables
.venv\Scripts\python scripts/setup_database.py

# 4. Load data
.venv\Scripts\python -m src.db.loader data/raw
```

**Access:**
- Host: `localhost:5432`
- Database: `form13f`
- User: `form13f_user`
- Password: `changeme123`

### Option 2: Supabase (Cloud Production)

**Best for:** Production deployment, team sharing, automatic backups

```bash
# 1. Get Supabase connection string
#    Go to: Supabase Dashboard → Settings → Database → Connection String (URI)
#    Copy the URI and update .env.supabase

# 2. Switch to Supabase environment
scripts\use-supabase.bat

# 3. Create tables (runs on Supabase)
.venv\Scripts\python scripts/setup_database.py

# 4. Load data (inserts into Supabase)
.venv\Scripts\python -m src.db.loader data/raw
```

**Access:**
- Supabase Dashboard: https://supabase.com/dashboard
- Table Editor: View/edit data in browser
- SQL Editor: Run custom queries

## Switching Between Environments

### Use Docker
```bash
scripts\use-docker.bat
# Now all commands use Docker
```

### Use Supabase
```bash
scripts\use-supabase.bat
# Now all commands use Supabase
```

## Environment Files

- **`.env.local`** - Docker PostgreSQL configuration
- **`.env.supabase`** - Supabase PostgreSQL configuration
- **`.env`** - Active configuration (created by scripts)

**Important:** `.env` is gitignored, but `.env.local` and `.env.supabase` are templates you can commit (without real passwords).

## Supabase Setup (First Time)

### 1. Create Supabase Project

1. Go to https://supabase.com
2. Create new project
3. Choose region (closest to you)
4. Set database password (save this!)

### 2. Get Connection String

1. Go to **Settings** → **Database**
2. Scroll to **Connection String**
3. Select **URI** mode
4. Copy the string (looks like):
   ```
   postgresql://postgres.xxxxx:[YOUR-PASSWORD]@aws-0-us-west-1.pooler.supabase.com:5432/postgres
   ```

### 3. Update Configuration

Edit `.env.supabase`:
```bash
DATABASE_URL=postgresql://postgres.xxxxx:[YOUR-PASSWORD]@aws-0-us-west-1.pooler.supabase.com:5432/postgres
```

Replace `[YOUR-PASSWORD]` with your actual database password.

## Database Operations

### Create Tables (Run Once)
```bash
.venv\Scripts\python scripts/setup_database.py
```

This runs the SQL schema file (`schema/001_initial_schema.sql`) that creates:
- `managers` table
- `issuers` table
- `filings` table
- `holdings` table
- All indexes and constraints

### Load Data
```bash
# Load Q2 2025 data (8,483 filings, 3.36M holdings)
.venv\Scripts\python -m src.db.loader data/raw
```

Expected time:
- **Docker (local):** ~2-3 minutes
- **Supabase (cloud):** ~5-8 minutes (network overhead)

### Verify Data

#### Using Python
```python
from src.db import SessionLocal
from sqlalchemy import text

with SessionLocal() as session:
    # Count records
    result = session.execute(text("SELECT COUNT(*) FROM filings")).scalar()
    print(f"Filings: {result:,}")

    result = session.execute(text("SELECT COUNT(*) FROM holdings")).scalar()
    print(f"Holdings: {result:,}")
```

#### Using Supabase Dashboard
1. Go to **Table Editor**
2. Click on `filings`, `holdings`, etc.
3. Browse data visually

#### Using psql (Docker only)
```bash
docker compose exec postgres psql -U form13f_user -d form13f

# Run queries
SELECT COUNT(*) FROM filings;
SELECT COUNT(*) FROM holdings;
SELECT * FROM managers LIMIT 10;
\q
```

## Common Issues

### Docker: "Connection refused"
- Make sure Docker Desktop is running
- Run: `docker compose ps` to check status
- Run: `docker compose up -d postgres` to start

### Supabase: "Connection timed out"
- Check your internet connection
- Verify connection string is correct
- Check Supabase project is not paused (free tier pauses after 7 days inactivity)

### Alembic: "Target database is not up to date"
- Run: `.venv\Scripts\alembic upgrade head`
- Or check: `.venv\Scripts\alembic current`

## Architecture

```
Development Flow:
┌─────────────┐         ┌─────────────┐
│   Docker    │         │  Supabase   │
│  (Local)    │         │  (Cloud)    │
└─────────────┘         └─────────────┘
      ↑                        ↑
      │                        │
      └────────────┬───────────┘
                   │
            .env file determines
              which one to use
                   │
                   ↓
           ┌──────────────┐
           │ Your App     │
           │ - Alembic    │
           │ - Loader     │
           │ - API        │
           └──────────────┘
```

## Best Practices

1. **Local development:** Use Docker
   - Fast iteration
   - No network latency
   - Can reset easily

2. **Testing with real data:** Use Docker
   - Load full dataset
   - Run experiments
   - No cloud costs

3. **Production/Deployment:** Use Supabase
   - Always available
   - Automatic backups
   - Team can access

4. **Keep both in sync:**
   ```bash
   # Dump from Docker
   docker compose exec postgres pg_dump -U form13f_user form13f > backup.sql

   # Load to Supabase
   psql "postgresql://postgres.xxxxx:password@...supabase.com:5432/postgres" < backup.sql
   ```

## Next Steps

After loading data:
- **Phase 3:** Build SQL Query Tool with Claude
- **Phase 4:** Create Agent that generates SQL from natural language
- **Phase 5:** Build FastAPI backend
- **Phase 6:** Build Streamlit UI

The database layer (Phase 2) works identically with both Docker and Supabase!
