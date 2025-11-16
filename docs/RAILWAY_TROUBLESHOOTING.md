# Railway Deployment Troubleshooting Guide

This guide helps diagnose and fix common Railway deployment issues for the Form 13F AI Agent.

## Current Issue: Database Connection Failure

### Symptoms
- Health endpoint shows: `"database": "disconnected"`
- API returns: `500 Internal Server Error`
- Streamlit UI shows: `Failed to fetch stats: The read operation timed out`

### Diagnosis Steps

#### 1. Check DATABASE_URL Environment Variable

**In Railway Dashboard:**
1. Go to your project → Select "form13f_aiagent" service
2. Click "Variables" tab
3. Verify `DATABASE_URL` is set

**Expected format:**
```
postgresql://postgres:YOUR_PASSWORD@db.PROJECT_ID.supabase.co:5432/postgres
```

**Common mistakes:**
- Missing the variable entirely
- Wrong port (use 5432 for direct connection, 6543 for connection pooler)
- Wrong password
- Wrong host (should be `db.PROJECT_ID.supabase.co`)

#### 2. Verify Supabase Connection Settings

**In Supabase Dashboard:**
1. Go to Project Settings → Database
2. Check "Connection Pooling" section
3. **IMPORTANT**: For Railway, you need to use either:
   - **Direct connection** (port 5432) - Limited to 100 connections
   - **Connection pooler** (port 6543) - Recommended for production

**If using connection pooler (port 6543):**
```
DATABASE_URL=postgresql://postgres.PROJECT_ID:PASSWORD@aws-1-us-east-2.pooler.supabase.com:6543/postgres
```

**If using direct connection (port 5432):**
```
DATABASE_URL=postgresql://postgres:PASSWORD@db.PROJECT_ID.supabase.co:5432/postgres
```

#### 3. Check Supabase IP Whitelisting

**In Supabase Dashboard:**
1. Go to Project Settings → Database → Connection Pooling
2. Check if "Restrict access to trusted IP addresses" is enabled
3. If enabled, you need to whitelist Railway's IP addresses

**To find Railway's IP addresses:**
- Railway uses dynamic IPs, so you may need to disable IP restrictions
- Or use Supabase's "Allow all IP addresses" option (less secure)

#### 4. Test Connection from Railway

**Add a test endpoint to verify:**

We've created a diagnostic script at `scripts/test_db_connection.py`. To run it on Railway:

```bash
# SSH into Railway container (if available) or add temporary endpoint
railway run python scripts/test_db_connection.py
```

Or create a temporary `/debug/db` endpoint in `src/api/main.py`:

```python
@app.get("/debug/db")
async def debug_db():
    """Debug database connection"""
    import subprocess
    result = subprocess.run(
        ["python", "scripts/test_db_connection.py"],
        capture_output=True,
        text=True
    )
    return {"stdout": result.stdout, "stderr": result.stderr}
```

Then visit: `https://your-app.up.railway.app/debug/db`

## Common Solutions

### Solution 1: Fix DATABASE_URL Format

The most common issue is incorrect DATABASE_URL format.

**Check in Railway:**
1. Go to Variables tab
2. Click on DATABASE_URL
3. Verify it matches this format exactly:
   ```
   postgresql://postgres:PASSWORD@HOST:PORT/postgres
   ```

**For Supabase**, get the correct URL from:
- Supabase Dashboard → Settings → Database → Connection String
- Choose "URI" format
- Make sure to replace `[YOUR-PASSWORD]` with actual password

### Solution 2: Use Connection Pooler (Recommended)

If you're hitting connection limits, switch to connection pooler:

1. In Supabase Dashboard → Settings → Database
2. Copy the "Connection Pooling" URL (port 6543)
3. Update DATABASE_URL in Railway:
   ```
   postgresql://postgres.PROJECT_ID:PASSWORD@aws-1-us-east-2.pooler.supabase.com:6543/postgres?pgbouncer=true
   ```

### Solution 3: Disable IP Whitelisting (Temporary)

For testing, disable IP restrictions:

1. Supabase Dashboard → Settings → Database
2. Under "Connection Pooling", disable IP restrictions
3. Re-deploy Railway app
4. Test connection

**Note**: Re-enable IP restrictions after confirming connection works.

### Solution 4: Increase Pool Size

Update `src/api/main.py` to use larger connection pool:

```python
_health_check_engine = create_engine(
    database_url,
    pool_size=5,  # Increase from 1
    max_overflow=10,  # Allow overflow
    pool_pre_ping=True,
    pool_recycle=3600  # Recycle connections every hour
)
```

## Verification Steps

After applying a fix:

### 1. Check Health Endpoint
```bash
curl https://your-app.up.railway.app/health
```

Expected response:
```json
{
  "status": "healthy",
  "database": "connected",  ← Should be "connected"
  "llm": "configured",
  "version": "0.1.0"
}
```

### 2. Check Stats Endpoint
```bash
curl https://your-app.up.railway.app/api/v1/stats
```

Expected response:
```json
{
  "managers_count": 123,
  "issuers_count": 456,
  "filings_count": 789,
  "holdings_count": 3360000,
  "latest_quarter": "2024-12-31",
  "total_value": 123456789
}
```

### 3. Check Railway Logs
```bash
railway logs
```

Look for:
- ✅ `Database connection successful`
- ❌ `Database connection failed: ...`

## Environment Variables Checklist

Make sure these are set in Railway:

```bash
# Required
DATABASE_URL=postgresql://postgres:PASSWORD@HOST:PORT/postgres
ANTHROPIC_API_KEY=sk-ant-your-key-here

# Recommended
LLM_PROVIDER=anthropic
LLM_MODEL=claude-3-5-sonnet-20241022
LOG_LEVEL=INFO
ENVIRONMENT=production
```

## Still Having Issues?

### Get Detailed Logs

1. Add this to `src/api/main.py` startup:
   ```python
   logger.info(f"DATABASE_URL: {database_url[:50]}...")  # First 50 chars only
   ```

2. Check Railway logs for the actual connection string being used

3. Verify it matches your Supabase credentials

### Contact Support

If none of these solutions work:

1. **Check Supabase Status**: https://status.supabase.com/
2. **Check Railway Status**: https://status.railway.app/
3. **Review Supabase Logs**: Supabase Dashboard → Logs → Postgres Logs
4. **Review Railway Logs**: `railway logs --limit 100`

## Quick Reference

### Supabase Connection Strings

**Direct connection (port 5432):**
- Good for: Low traffic, development
- Limit: ~100 concurrent connections
- Format: `postgresql://postgres:PASSWORD@db.PROJECT_ID.supabase.co:5432/postgres`

**Connection pooler (port 6543):**
- Good for: Production, high traffic
- Limit: Thousands of connections
- Format: `postgresql://postgres.PROJECT_ID:PASSWORD@aws-1-us-east-2.pooler.supabase.com:6543/postgres?pgbouncer=true`

**Transaction mode vs Session mode:**
- Transaction mode: Recommended for most apps (our app uses this)
- Session mode: Required for migrations, alembic

### Railway Commands

```bash
# View logs
railway logs

# Check environment variables
railway variables

# Restart service
railway restart

# Force redeploy
railway up --detach
```

## Success Checklist

- [ ] DATABASE_URL is set in Railway
- [ ] DATABASE_URL format is correct (postgresql://...)
- [ ] Password is correct (from Supabase dashboard)
- [ ] Host/port are correct (5432 or 6543)
- [ ] Supabase IP restrictions are disabled (or Railway IPs whitelisted)
- [ ] Health endpoint shows `"database": "connected"`
- [ ] Stats endpoint returns data
- [ ] No errors in Railway logs
