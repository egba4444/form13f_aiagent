# Setting Up Qdrant on Railway

## Quick Guide: Deploy Qdrant as a Separate Service on Railway

Since you want to use Railway for Qdrant, here's how to set it up:

### Step 1: Add Qdrant Service to Your Railway Project

1. **Open your Railway project dashboard**
   - Go to https://railway.app
   - Select your `form13f_aiagent` project

2. **Create new service for Qdrant**
   - Click "New" → "Empty Service"
   - Name it: `qdrant`

3. **Configure Docker deployment**
   - Go to the service Settings
   - Under "Source" section, click "Deploy from Docker Image"
   - Enter image: `qdrant/qdrant:latest`
   - Click "Deploy"

4. **Add persistent volume**
   - In the same service, go to "Settings" → "Volumes"
   - Click "New Volume"
   - Mount path: `/qdrant/storage`
   - Size: Start with 1GB (can increase later)
   - Click "Add"

5. **Generate domain (for external access)**
   - Go to "Settings" → "Networking"
   - Click "Generate Domain"
   - You'll get a URL like: `qdrant-production-xxxx.up.railway.app`

6. **Add environment variable (optional)**
   - Go to "Variables"
   - Add: `QDRANT__SERVICE__GRPC_PORT=6334`

### Step 2: Configure Internal Networking

Railway provides automatic internal networking between services in the same project.

**Internal URL format:**
```
http://qdrant.railway.internal:6333
```

This is the recommended approach because:
- ✅ Free internal networking (no data transfer costs)
- ✅ Lower latency
- ✅ More secure (not exposed to internet)
- ✅ No rate limits

### Step 3: Update Your API Service

1. **Go to your API service in Railway**
   - Select your existing API service (form13f_aiagent)

2. **Add Qdrant URL variable**
   - Go to "Variables"
   - Add new variable:
     ```
     QDRANT_URL=http://qdrant.railway.internal:6333
     ```
   - Railway will automatically redeploy when you save

### Step 4: Verify Qdrant is Running

After deployment:

1. **Check Qdrant service logs**
   - Click on Qdrant service
   - Go to "Deployments" → Click latest deployment
   - Check logs for: `Qdrant gRPC listening on 0.0.0.0:6334`

2. **Test from API service**
   ```bash
   # Using Railway CLI or API logs, you should see:
   # "RAG tool initialized successfully" when API starts
   ```

## Alternative: Use Public URL

If you prefer to use the public Qdrant URL (generated domain):

1. **Copy the generated domain** from Qdrant service networking settings
2. **Update API variable:**
   ```
   QDRANT_URL=https://qdrant-production-xxxx.up.railway.app
   ```

Note: Using public URL incurs data transfer costs on Railway.

## Cost Considerations

### Internal Networking (Recommended)
- **Cost:** Free (included in Railway plan)
- **Data transfer:** No cost between services
- **Best for:** Production use

### Public Domain
- **Cost:** $0.10/GB for data egress
- **Use case:** External tools, development

**Recommendation:** Use internal URL (`qdrant.railway.internal:6333`)

## Railway Environment Variables Summary

After setup, your API service should have:

```bash
# Database (automatically provided by Railway)
DATABASE_URL=postgresql://...

# Qdrant (add this)
QDRANT_URL=http://qdrant.railway.internal:6333

# LLM Provider
ANTHROPIC_API_KEY=sk-ant-...

# Auth
SUPABASE_URL=https://...
SUPABASE_KEY=...
```

## Deployment Order

1. ✅ Deploy Qdrant service first (wait for it to be healthy)
2. ✅ Add QDRANT_URL to API service
3. ✅ Redeploy API service (happens automatically)
4. ✅ Verify connection via health endpoint

## Verify Setup

After both services are deployed:

```bash
# Check health endpoint
curl https://your-api.railway.app/health

# Should return:
{
  "status": "healthy",
  "database": "connected",
  "llm": "configured",
  "version": "0.1.0"
}

# Test semantic search
curl https://your-api.railway.app/api/v1/search/semantic \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "top_k": 1}'
```

## Volume Size Planning

**Current needs (11 embeddings):**
- Storage: <1MB
- Volume: 1GB is more than enough

**After full ingestion (~8,500 embeddings):**
- Estimated: ~300MB
- Recommended volume: 1GB (leaves room for growth)

**Future growth:**
- 1GB can handle ~30,000 embeddings (384 dimensions)
- Can increase volume size anytime in Railway settings

## Troubleshooting

### Qdrant service won't start

**Check:**
1. Docker image is correct: `qdrant/qdrant:latest`
2. Volume is mounted at: `/qdrant/storage`
3. Logs for errors (Settings → Deployments → View Logs)

### API can't connect to Qdrant

**Check:**
1. Both services are in same Railway project
2. QDRANT_URL uses internal networking: `http://qdrant.railway.internal:6333`
3. Qdrant service is running (check status)
4. API logs show RAG initialization errors

**Fix:**
```bash
# Test connection from API service using Railway CLI
railway run -s api python -c "from qdrant_client import QdrantClient; client = QdrantClient('http://qdrant.railway.internal:6333'); print(client.get_collections())"
```

### Collection not found

This is normal on first deployment. The collection will be auto-created when:
1. You run the embedding generation script, OR
2. First semantic search is performed

## Running Embedding Generation on Railway

After deployment, generate embeddings in production:

```bash
# Option 1: Using Railway CLI
railway run -s api python scripts/generate_embeddings.py --recreate

# Option 2: Add as one-time job in Railway
# Create a new service, use same image, different start command
```

## Migration from Local Qdrant

Your local Qdrant data (11 embeddings) will NOT automatically transfer. You have two options:

### Option 1: Re-generate in Production (Recommended)
```bash
# After deployment, run:
railway run -s api python scripts/extract_filing_text.py
railway run -s api python scripts/generate_embeddings.py --recreate
```

### Option 2: Export/Import
Export locally, import to Railway Qdrant. (More complex, not recommended)

## Railway Service Summary

After setup, your project should have:

```
form13f_aiagent (Railway Project)
├── postgres (managed database)
├── api (your FastAPI app)
└── qdrant (vector database) ← NEW
```

## Quick Setup Checklist

- [ ] Created Qdrant service in Railway
- [ ] Deployed `qdrant/qdrant:latest` Docker image
- [ ] Added volume at `/qdrant/storage` (1GB)
- [ ] Generated domain (optional)
- [ ] Added `QDRANT_URL` variable to API service
- [ ] Waited for API service to redeploy
- [ ] Checked health endpoint
- [ ] Verified RAG tool initialization in logs

## Next Steps After Qdrant is Running

1. Wait for text extraction to finish (currently running)
2. Deploy API service with new code
3. Run embedding generation:
   ```bash
   railway run -s api python scripts/generate_embeddings.py --recreate
   ```
4. Test semantic search
5. Deploy Streamlit UI

---

**Estimated Time:** 10-15 minutes for Qdrant setup on Railway
