# Railway Deployment Guide

Complete guide for deploying the Form 13F AI Agent on Railway.app

## Why Railway?

**Benefits:**
- ✅ **Free tier**: $5 credit/month (enough for development)
- ✅ **Docker support**: Uses your existing Dockerfile
- ✅ **Auto-deploy**: Push to GitHub → automatic deployment
- ✅ **Environment variables**: Easy secrets management
- ✅ **Custom domains**: Free HTTPS
- ✅ **Database included**: PostgreSQL service (or use Supabase)
- ✅ **Simple CLI**: Deploy from command line

## Prerequisites

1. **GitHub account** with your repository
2. **Railway account** (sign up at https://railway.app)
3. **Supabase database** (already configured) OR Railway PostgreSQL

## Quick Start (3 Steps)

### Step 1: Connect GitHub to Railway

1. Go to https://railway.app
2. Click **"Start a New Project"**
3. Select **"Deploy from GitHub repo"**
4. Authorize Railway to access your GitHub
5. Select your repository: `egba4444/form13f_aiagent`

### Step 2: Configure Environment Variables

Railway will ask for environment variables. Add these:

```bash
# Database (using your existing Supabase)
DATABASE_URL=postgresql://postgres:ispgW1VOhuCsSxvO@db.ocgueuyckdkpedxvbpge.supabase.co:5432/postgres

# LLM Configuration
LLM_PROVIDER=anthropic
LLM_MODEL=claude-3-5-sonnet-20241022
ANTHROPIC_API_KEY=sk-ant-your-actual-key-here
LLM_MAX_TOKENS=4096
LLM_TEMPERATURE=0.0

# Application
LOG_LEVEL=INFO
ENVIRONMENT=production
```

### Step 3: Deploy!

Railway will automatically:
1. Detect your `Dockerfile`
2. Build the Docker image
3. Deploy the container
4. Assign a URL (e.g., `form13f-aiagent.up.railway.app`)

**Done!** Your API will be live in ~5 minutes.

## Detailed Setup

### Option A: Deploy via GitHub (Recommended)

**1. Push your code to GitHub** (already done)

**2. Create Railway project:**
```bash
# Install Railway CLI (optional)
npm i -g @railway/cli

# Login
railway login

# Link to your repo
railway init
```

**3. Configure via Dashboard:**
- Go to https://railway.app/dashboard
- Select your project
- Click **Variables** tab
- Add all environment variables (see above)

**4. Deploy:**
- Push to GitHub → auto-deploys
- Or manually: `railway up`

### Option B: Deploy via CLI

```bash
# Install CLI
npm i -g @railway/cli

# Login
railway login

# Initialize project
cd form13f_aiagent
railway init

# Set environment variables
railway variables set DATABASE_URL="postgresql://..."
railway variables set ANTHROPIC_API_KEY="sk-ant-..."
railway variables set LLM_PROVIDER="anthropic"
railway variables set LLM_MODEL="claude-3-5-sonnet-20241022"

# Deploy
railway up
```

### Option C: Deploy via Dashboard Only

1. Go to https://railway.app/new
2. Click **"Empty Project"**
3. Click **"GitHub Repo"**
4. Select `egba4444/form13f_aiagent`
5. Add environment variables
6. Click **"Deploy"**

## Environment Variables Reference

### Required

```bash
# Database
DATABASE_URL="postgresql://user:pass@host:5432/db"

# LLM API Key (at least one)
ANTHROPIC_API_KEY="sk-ant-..."
# OR
OPENAI_API_KEY="sk-..."
# OR
GEMINI_API_KEY="..."
```

### Recommended

```bash
# LLM Configuration
LLM_PROVIDER="anthropic"           # anthropic, openai, gemini, etc.
LLM_MODEL="claude-3-5-sonnet-20241022"
LLM_MAX_TOKENS="4096"
LLM_TEMPERATURE="0.0"

# Application
LOG_LEVEL="INFO"                   # DEBUG, INFO, WARNING, ERROR
ENVIRONMENT="production"
```

### Optional

```bash
# Rate Limiting
RATE_LIMIT_PER_MINUTE="100"

# CORS (if needed for frontend)
CORS_ORIGINS="https://yourdomain.com"
```

## Database Options

### Option 1: Use Supabase (Current Setup)

**Pros:**
- Already configured
- Supabase dashboard for data viewing
- Automatic backups

**Setup:**
```bash
DATABASE_URL=postgresql://postgres:[password]@db.ocgueuyckdkpedxvbpge.supabase.co:5432/postgres
```

### Option 2: Use Railway PostgreSQL

**Pros:**
- Everything in one place
- Free tier includes PostgreSQL
- Automatic backups

**Setup:**
1. In Railway dashboard, click **"New"** → **"Database"** → **"PostgreSQL"**
2. Railway will create database and set `DATABASE_URL` automatically
3. Run migrations:
   ```bash
   railway run python scripts/setup_database.py
   ```

### Option 3: Use Both (Recommended for Production)

**Development:** Railway PostgreSQL
**Production:** Supabase

Switch with environment variables.

## Deployment Workflow

### Automatic Deployment (GitHub)

1. **Make changes** to your code
2. **Commit and push** to GitHub:
   ```bash
   git add .
   git commit -m "Your changes"
   git push
   ```
3. **Railway auto-deploys** (takes ~3-5 minutes)
4. **Check logs** in Railway dashboard

### Manual Deployment (CLI)

```bash
# Deploy current directory
railway up

# Watch logs
railway logs

# Open in browser
railway open
```

## Accessing Your Deployment

### URLs

Railway provides:
- **API URL**: `https://form13f-aiagent-production.up.railway.app`
- **Health Check**: `https://your-app.up.railway.app/health`
- **API Docs**: `https://your-app.up.railway.app/docs`

### Custom Domain

1. Go to Railway dashboard → **Settings** → **Domains**
2. Click **"Add Custom Domain"**
3. Enter your domain (e.g., `api.yourdomain.com`)
4. Add CNAME record to your DNS:
   ```
   CNAME api -> your-app.up.railway.app
   ```
5. Railway auto-provisions SSL certificate

## Running Migrations

### First Deployment

After deploying, create database tables:

**Via Railway CLI:**
```bash
railway run python scripts/setup_database.py
```

**Via Dashboard:**
1. Go to **Deployments** tab
2. Find latest deployment
3. Click **"..."** → **"Run Command"**
4. Enter: `python scripts/setup_database.py`

### Loading Data

**Option 1: From your laptop (recommended for large datasets)**
```bash
# Set Railway DATABASE_URL locally
export DATABASE_URL="postgresql://..."

# Load data
python -m src.ingestion.ingest
```

**Option 2: On Railway (might timeout)**
```bash
railway run python -m src.ingestion.ingest
```

## Monitoring

### View Logs

**Via CLI:**
```bash
railway logs
railway logs --tail  # Follow logs
```

**Via Dashboard:**
- Click **Deployments** → **View Logs**

### Health Check

```bash
curl https://your-app.up.railway.app/health
```

Should return:
```json
{
  "status": "healthy",
  "database": "connected",
  "version": "0.1.0"
}
```

### Metrics

Railway dashboard shows:
- CPU usage
- Memory usage
- Network traffic
- Request count

## Scaling

### Vertical Scaling (More Resources)

Railway free tier:
- **CPU**: Shared
- **RAM**: 512MB
- **Disk**: 1GB

Upgrade to Pro ($5/month):
- **CPU**: Dedicated vCPU
- **RAM**: Up to 8GB
- **Disk**: Up to 100GB

### Horizontal Scaling (Multiple Instances)

Railway supports multiple replicas (Pro plan):
```bash
railway scale --replicas 3
```

## Troubleshooting

### Build Fails

**Problem**: Docker build fails

**Solutions**:
1. Check `Dockerfile` is valid
2. Verify all dependencies in `pyproject.toml`
3. Check Railway build logs
4. Test locally: `docker build -t test .`

### Database Connection Fails

**Problem**: `could not connect to database`

**Solutions**:
1. Verify `DATABASE_URL` is set correctly
2. Check Supabase project is active (not paused)
3. Test connection locally:
   ```bash
   railway run python -c "from sqlalchemy import create_engine; engine = create_engine('$DATABASE_URL'); print(engine.connect())"
   ```

### Out of Memory

**Problem**: Container crashes with OOM error

**Solutions**:
1. Reduce `LLM_MAX_TOKENS` (less memory per request)
2. Upgrade Railway plan (more RAM)
3. Optimize code (reduce memory usage)

### Slow Responses

**Problem**: API takes too long to respond

**Solutions**:
1. Check database is in same region as Railway
2. Use Railway PostgreSQL instead of Supabase
3. Add database indexes
4. Use Claude Haiku (faster model)

### Environment Variables Not Loading

**Problem**: App can't find env vars

**Solutions**:
1. Check variables are set in Railway dashboard
2. Restart deployment
3. Verify `.env` file is gitignored (don't commit secrets!)

## Cost Estimation

### Free Tier ($5 credit/month)

**Included:**
- 500 hours compute time
- 100GB network egress
- 1GB disk
- Shared CPU
- 512MB RAM

**Good for:**
- Development
- Personal projects
- Low traffic (< 1000 requests/day)

**Cost breakdown:**
- API running 24/7: ~$3/month
- PostgreSQL running 24/7: ~$2/month
- **Total**: ~$5/month (covered by free tier!)

### Hobby Plan ($5/month)

**Included:**
- Everything in free tier
- +$5 credit
- Priority support

**Good for:**
- Production apps
- Moderate traffic (< 10k requests/day)

### Pro Plan ($20/month)

**Included:**
- Dedicated CPU
- Up to 8GB RAM
- Up to 100GB disk
- Horizontal scaling

**Good for:**
- High traffic apps
- Production workloads
- Multiple services

## Best Practices

### 1. Use Environment-Specific Configs

```bash
# Development
ENVIRONMENT=development
LOG_LEVEL=DEBUG

# Production
ENVIRONMENT=production
LOG_LEVEL=INFO
```

### 2. Enable Auto-Deploy from Main Branch

Railway dashboard → **Settings** → **Auto-Deploy**
- ✅ Enable for `main` branch
- ❌ Disable for feature branches (deploy manually)

### 3. Use Railway Secrets for Sensitive Data

Never commit:
- API keys
- Database passwords
- Secret tokens

Always use Railway environment variables.

### 4. Set Up Health Checks

Railway pings `/health` every 30 seconds. Make sure it returns 200 OK.

### 5. Monitor Logs

Set up log drains to external services:
- Datadog
- Logtail
- Better Stack

Railway dashboard → **Integrations** → **Log Drains**

### 6. Use Railway Volumes for Persistent Data

If you need to store files:
```bash
railway volume create --name data
railway volume attach data --mount /app/data
```

## CI/CD Integration

### GitHub Actions (Optional)

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Railway

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Install Railway CLI
        run: npm i -g @railway/cli

      - name: Deploy to Railway
        run: railway up
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
```

Get `RAILWAY_TOKEN`:
```bash
railway login
railway whoami --token
```

Add to GitHub secrets: Settings → Secrets → New repository secret

## Next Steps

1. **Deploy API** (Phase 5):
   ```bash
   git push  # Auto-deploys to Railway
   ```

2. **Test deployment**:
   ```bash
   curl https://your-app.up.railway.app/health
   curl -X POST https://your-app.up.railway.app/api/v1/query \
     -H "Content-Type: application/json" \
     -d '{"query": "How many managers are in the database?"}'
   ```

3. **Deploy UI** (Phase 6):
   - Create separate Railway service for Streamlit
   - Point to same database

4. **Monitor and scale** as needed

## Resources

- **Railway Docs**: https://docs.railway.app
- **Railway Discord**: https://discord.gg/railway
- **Railway Templates**: https://railway.app/templates
- **Pricing**: https://railway.app/pricing

---

**Last Updated**: 2025-01-12
**Version**: 1.0
