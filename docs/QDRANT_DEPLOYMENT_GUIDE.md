# Qdrant Deployment Guide for Production

## Deployment Options

You're deploying to Railway, so you have two options for Qdrant:

### Option 1: Add Qdrant to Railway (Recommended)

Railway doesn't have a native Qdrant service, but you can deploy it as a Docker container.

**Steps:**

1. **Add Qdrant Service to Railway Project**
   ```bash
   # In your Railway project dashboard:
   # 1. Click "New" → "Empty Service"
   # 2. Name it "qdrant"
   # 3. In Settings → Deploy:
   #    - Set Docker Image: qdrant/qdrant:latest
   # 4. In Settings → Networking:
   #    - Generate Domain (or use internal URL)
   # 5. In Settings → Variables:
   #    - Add: QDRANT__SERVICE__GRPC_PORT=6334
   ```

2. **Configure Volume for Persistence**
   ```bash
   # In Railway Qdrant service:
   # Settings → Volumes → Add Volume
   # Mount Path: /qdrant/storage
   # Size: 1GB (increase as needed)
   ```

3. **Get Qdrant Internal URL**
   ```bash
   # Railway provides internal networking
   # Format: qdrant.railway.internal:6333
   # Or use the public domain Railway generates
   ```

4. **Update API Service Environment Variable**
   ```bash
   # In your API service on Railway:
   # Settings → Variables → Add:
   QDRANT_URL=http://qdrant.railway.internal:6333
   # OR if using public domain:
   QDRANT_URL=https://qdrant-production-xxxx.up.railway.app
   ```

### Option 2: Use Qdrant Cloud (Easiest)

**Steps:**

1. **Sign up for Qdrant Cloud**
   - Go to https://cloud.qdrant.io
   - Create free account
   - Create a cluster (1GB free tier available)

2. **Get Cluster URL and API Key**
   ```bash
   # From Qdrant Cloud dashboard:
   # Cluster URL: https://xxx-xxx-xxx.cloud.qdrant.io:6333
   # API Key: qdr_xxxxxxxxxxxxx
   ```

3. **Update Railway Environment Variables**
   ```bash
   # In your API service on Railway:
   QDRANT_URL=https://xxx-xxx-xxx.cloud.qdrant.io:6333
   QDRANT_API_KEY=qdr_xxxxxxxxxxxxx  # If required
   ```

4. **Update Code for API Key (if needed)**
   ```python
   # src/rag/vector_store.py - add API key support
   # Already supports URL from config, just verify
   ```

## Recommended Approach for Railway

**Use Qdrant Cloud (Option 2)** because:
- ✅ Easier setup (no Docker configuration)
- ✅ Managed service (automatic backups, updates)
- ✅ Free tier available (1GB storage)
- ✅ Better reliability and performance
- ✅ No volume management needed

## Quick Start: Qdrant Cloud Setup

### Step 1: Create Qdrant Cloud Account

1. Go to https://cloud.qdrant.io
2. Sign up with email
3. Verify email

### Step 2: Create Cluster

1. Click "Create Cluster"
2. Choose plan:
   - **Free Tier**: 1GB storage (good for ~10,000 embeddings)
   - **Paid**: $25/month for more storage
3. Select region (closest to your Railway deployment)
4. Name: `form13f-production`
5. Click "Create"

### Step 3: Get Connection Details

1. Click on your cluster
2. Copy **Cluster URL**: `https://xxx.cloud.qdrant.io:6333`
3. (Optional) Create API key if required

### Step 4: Update Railway Environment Variables

1. Go to Railway dashboard
2. Select your API service
3. Go to "Variables" tab
4. Add/Update:
   ```
   QDRANT_URL=https://xxx-xxx-xxx.cloud.qdrant.io:6333
   ```
5. Redeploy service

### Step 5: Verify Connection

After deployment, test Qdrant connection:

```bash
# Using Railway CLI or your deployment URL
curl https://your-api.railway.app/health

# Should show Qdrant as connected in logs
# Or test directly:
curl https://your-api.railway.app/api/v1/search/semantic \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "top_k": 1}'
```

## Migration: Transfer Existing Embeddings

If you've already created embeddings locally and want to move them to production:

### Method 1: Re-generate in Production

**Recommended** - Most reliable:

```bash
# After deployment, run in production:
railway run python scripts/extract_filing_text.py --all
railway run python scripts/generate_embeddings.py --recreate
```

### Method 2: Export and Import

If you want to transfer local embeddings:

```python
# Create export script: scripts/export_qdrant.py
from qdrant_client import QdrantClient
import json

# Export from local
local_client = QdrantClient("http://localhost:6333")
points = local_client.scroll(
    collection_name="filing_text_embeddings",
    limit=10000
)[0]

# Save to file
with open("embeddings_export.json", "w") as f:
    json.dump([p.dict() for p in points], f)

# Import to production
prod_client = QdrantClient(
    url="https://xxx.cloud.qdrant.io:6333",
    api_key="your-api-key"  # if required
)

# Recreate collection
from src.rag.vector_store import VectorStore
vector_store = VectorStore(config)
vector_store.create_collection()

# Upload points
prod_client.upsert(
    collection_name="filing_text_embeddings",
    points=points
)
```

## Environment Variables Checklist

Make sure these are set in Railway:

```bash
# Required
DATABASE_URL=postgresql://...  # Railway provides this
QDRANT_URL=https://xxx.cloud.qdrant.io:6333

# LLM Provider
ANTHROPIC_API_KEY=sk-ant-...

# Authentication
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=xxx

# Optional
QDRANT_API_KEY=xxx  # Only if Qdrant Cloud requires it
```

## Verify Qdrant is Working

### Check 1: Health Endpoint

```bash
curl https://your-api.railway.app/health
```

Expected response:
```json
{
  "status": "healthy",
  "database": "connected",
  "llm": "configured",
  "version": "0.1.0"
}
```

### Check 2: Qdrant Direct

```bash
# Test Qdrant directly
curl https://xxx.cloud.qdrant.io:6333/collections
```

Expected response:
```json
{
  "result": {
    "collections": [
      {
        "name": "filing_text_embeddings"
      }
    ]
  }
}
```

### Check 3: Semantic Search

```bash
curl https://your-api.railway.app/api/v1/search/semantic \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"query": "test query", "top_k": 3}'
```

## Troubleshooting

### Error: "Cannot connect to Qdrant"

**Check:**
1. QDRANT_URL is correct in Railway variables
2. Qdrant Cloud cluster is running
3. API service can reach Qdrant URL (check Railway logs)
4. Firewall rules allow connection

**Fix:**
```bash
# Test connection from Railway:
railway run python -c "from qdrant_client import QdrantClient; \
  client = QdrantClient('$QDRANT_URL'); \
  print(client.get_collections())"
```

### Error: "Collection not found"

**Fix:**
```bash
# Create collection by triggering API:
curl https://your-api.railway.app/api/v1/search/semantic \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "top_k": 1}'

# This will auto-create the collection on first use
```

### Error: "No embeddings found"

**Fix:**
```bash
# Run embedding generation in production:
railway run python scripts/generate_embeddings.py
```

## Production Deployment Checklist

- [ ] Qdrant Cloud account created
- [ ] Cluster created and running
- [ ] QDRANT_URL added to Railway environment variables
- [ ] API service redeployed
- [ ] Health endpoint shows connected
- [ ] Test semantic search endpoint
- [ ] (Optional) Run historical data ingestion
- [ ] Monitor Qdrant Cloud dashboard for usage

## Cost Estimation

**Qdrant Cloud Free Tier:**
- 1GB storage
- ~10,000 embeddings (384 dimensions)
- Sufficient for testing and small production

**For Full Dataset (8,483 filings):**
- Estimated: ~8,500 embeddings
- Storage needed: ~300MB
- **Free tier is sufficient!** ✅

**If you exceed free tier:**
- $25/month for 4GB (plenty for growth)

## Next Steps After Qdrant is Running

1. ✅ Qdrant deployed and accessible
2. Deploy API code to Railway
3. Deploy Streamlit UI to Railway
4. Test all endpoints
5. Run historical data ingestion:
   ```bash
   railway run python scripts/extract_filing_text.py --all
   railway run python scripts/generate_embeddings.py --recreate
   ```
6. Verify embeddings in Qdrant Cloud dashboard
7. Test semantic search with real queries

---

**Recommended:** Use Qdrant Cloud (free tier) for simplest setup! 🚀
