# Railway Deployment Guide

## Quick Start (5 minutes)

### 1. Login to Railway

Open PowerShell or Command Prompt and run:
```bash
railway login
```

This will open your browser. Sign in with GitHub.

### 2. Run Deployment Script

After logging in, run:
```bash
deploy_railway.bat
```

This script will:
- Initialize a new Railway project
- Configure environment variables
- Deploy your API

### 3. Set Your API Key

**IMPORTANT:** You must set your Anthropic API key manually:

```bash
railway variables --set ANTHROPIC_API_KEY=sk-ant-your-actual-key-here
```

Replace `sk-ant-your-actual-key-here` with your real Anthropic API key.

### 4. View Your Deployment

```bash
# Get your app's URL
railway domain

# Open in browser
railway open

# View logs
railway logs
```

Your API will be live at: `https://your-project.up.railway.app`

---

## Manual Deployment Steps

If you prefer to do it manually:

### Step 1: Login
```bash
railway login
```

### Step 2: Initialize Project
```bash
railway init
```

Choose "Empty Project" and give it a name like "form13f-aiagent"

### Step 3: Link to Service
```bash
railway link
```

### Step 4: Set Environment Variables

Set these one by one:
```bash
# Database (Supabase)
railway variables --set DATABASE_URL="postgresql://postgres:ispgW1VOhuCsSxvO@db.ocgueuyckdkpedxvbpge.supabase.co:5432/postgres"

# LLM Configuration
railway variables --set LLM_PROVIDER="anthropic"
railway variables --set LLM_MODEL="claude-3-5-sonnet-20241022"
railway variables --set LLM_MAX_TOKENS="4096"
railway variables --set LLM_TEMPERATURE="0.0"

# Your Anthropic API Key (REQUIRED!)
railway variables --set ANTHROPIC_API_KEY="sk-ant-your-key-here"

# Application Settings
railway variables --set LOG_LEVEL="INFO"
railway variables --set ENVIRONMENT="production"
```

### Step 5: Deploy
```bash
railway up
```

This will:
1. Build your Docker image
2. Push to Railway
3. Start your service
4. Generate a public URL

### Step 6: Verify Deployment

```bash
# Check status
railway status

# View logs
railway logs

# Get domain
railway domain
```

Visit: `https://your-domain.up.railway.app/docs`

---

## What Gets Deployed

Railway will:
1. Use your `Dockerfile` to build the image
2. Install all dependencies from `pyproject.toml`
3. Start the FastAPI server on port 8000
4. Automatically assign a public domain
5. Enable HTTPS

## Environment Variables

| Variable | Value | Required |
|----------|-------|----------|
| `DATABASE_URL` | Supabase connection string | ✅ Yes |
| `ANTHROPIC_API_KEY` | Your Claude API key | ✅ Yes |
| `LLM_PROVIDER` | `anthropic` | ✅ Yes |
| `LLM_MODEL` | `claude-3-5-sonnet-20241022` | ✅ Yes |
| `LLM_MAX_TOKENS` | `4096` | No (has default) |
| `LLM_TEMPERATURE` | `0.0` | No (has default) |
| `LOG_LEVEL` | `INFO` | No (has default) |
| `ENVIRONMENT` | `production` | No (has default) |

## Endpoints After Deployment

Your deployed API will have:

- **API Docs**: `https://your-domain.up.railway.app/docs`
- **Health Check**: `https://your-domain.up.railway.app/health`
- **Database Stats**: `https://your-domain.up.railway.app/api/v1/stats`
- **Query**: `https://your-domain.up.railway.app/api/v1/query` (POST)

## Testing Your Deployed API

```bash
# Health check
curl https://your-domain.up.railway.app/health

# Database stats
curl https://your-domain.up.railway.app/api/v1/stats

# Natural language query
curl -X POST https://your-domain.up.railway.app/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "How many managers are in the database?"}'
```

## Monitoring & Logs

```bash
# View real-time logs
railway logs -f

# View recent logs
railway logs

# Check deployment status
railway status

# View environment variables
railway variables
```

## Updating Your Deployment

After making code changes:

```bash
# Commit your changes
git add .
git commit -m "Update API"

# Deploy update
railway up
```

Railway will rebuild and redeploy automatically.

## Troubleshooting

### Deployment Failed

Check logs:
```bash
railway logs
```

Common issues:
- Missing `ANTHROPIC_API_KEY`
- Invalid `DATABASE_URL`
- Build failures (check Dockerfile)

### API Not Responding

1. Check if service is running:
   ```bash
   railway status
   ```

2. View logs:
   ```bash
   railway logs -f
   ```

3. Verify environment variables:
   ```bash
   railway variables
   ```

### Database Connection Issues

Verify Supabase connection:
```bash
railway run python -c "
from sqlalchemy import create_engine, text
import os
engine = create_engine(os.getenv('DATABASE_URL'))
with engine.connect() as conn:
    print('✅ Database connected!')
    result = conn.execute(text('SELECT COUNT(*) FROM managers'))
    print(f'Managers: {result.scalar()}')
"
```

## Cost Estimate

Railway Free Tier:
- $5/month in credits
- ~500 hours of usage
- Suitable for development/testing

For production:
- Starter Plan: $20/month
- Pro Plan: $50/month
- Includes more resources and usage

## Next Steps

1. ✅ Deploy to Railway
2. Load Form 13F data into Supabase
3. Test queries with real data
4. Monitor usage and costs
5. Consider adding:
   - Rate limiting
   - Authentication
   - Caching
   - Error tracking (Sentry)

## Support

- Railway Docs: https://docs.railway.app
- Railway Discord: https://discord.gg/railway
- This Project: https://github.com/egba4444/form13f_aiagent
