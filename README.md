# Form 13F AI Agent

> **Ask questions about institutional investor holdings in natural language**

A production-ready AI agent that transforms complex SEC Form 13F institutional holdings data into an interactive, conversational interface powered by Claude 3.5 Sonnet.

<div align="center">

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Streamlit-FF4B4B?style=for-the-badge&logo=streamlit)](https://form13faiagent-ia8jkydleycwabcjzeme4m.streamlit.app/)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql)](https://www.postgresql.org/)

**[🚀 Try Live Demo](https://form13faiagent-ia8jkydleycwabcjzeme4m.streamlit.app/) • [📖 Documentation](docs/) • [🐛 Report Issue](https://github.com/egba4444/form13f_aiagent/issues)**

</div>

## ✨ What Can You Do?

Ask questions about institutional investor holdings in plain English and get instant, accurate answers backed by SQL-powered data analysis:

- 💰 **"How many AAPL shares did Berkshire Hathaway hold in Q4 2024?"**
- 📊 **"What were BlackRock's top 5 holdings by value?"**
- 🔍 **"Show me all managers who held more than 10M shares of TSLA"**
- 📈 **"What was the total value of Vanguard's portfolio in Q3 2024?"**
- 🤖 **"Find filings that mention artificial intelligence"** (semantic search)

## 🎯 Key Features

- **🗣️ Natural Language Interface** - Ask questions like you're talking to an analyst
- **🔍 SQL-First Architecture** - Generates precise SQL queries for structured data (90% of queries)
- **🧠 RAG Semantic Search** - Search filing commentary and disclosures (10% of queries)
- **📊 Interactive Visualizations** - Portfolio composition, ownership analysis, top movers
- **🔒 Enterprise Security** - Multi-layer SQL validation, authentication, rate limiting
- **🚀 Production Ready** - Deployed on Railway (API) + Streamlit Cloud (UI)
- **📱 Multi-Modal Access** - REST API, Python SDK, and web interface

## 🏗️ Architecture

```
User Query (Natural Language)
    ↓
Claude 3.5 Sonnet Agent
    ↓
Generate SQL Query
    ↓
Execute on PostgreSQL
    ↓
Format Results
    ↓
Claude Generates Natural Language Answer
```

**Key Components:**
- **Data Ingestion**: Parse 13F-HR XML filings (stored in `data/raw/`)
- **PostgreSQL Database**: Structured storage of holdings and metadata
- **SQL Query Tool**: Claude generates safe, validated SQL queries
- **Agent**: Natural language → SQL → Answer pipeline
- **API**: FastAPI backend with REST endpoints and analytics
- **UI**: Streamlit multi-tab interface with interactive visualizations

**Future Enhancement (Phase 7):**
- Add RAG/vector store for unstructured commentary and explanatory notes

## 🛠️ Technology Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.11+ |
| LLM Provider | LiteLLM (100+ providers) |
| LLM | Claude 3.5 Sonnet (default) |
| Database | PostgreSQL 16+ (Supabase) |
| API Framework | FastAPI |
| UI | Streamlit |
| Visualizations | Plotly |
| ORM | SQLAlchemy 2.0 |
| HTTP Client | httpx |
| Testing | pytest |
| Package Manager | uv (10x faster than pip) |
| Deployment | Railway.app (API) + Streamlit Cloud (UI) |
| Containerization | Docker |

## 📋 Implementation Phases

| Phase | Description | Duration | Status |
|-------|-------------|----------|--------|
| **Phase 1** | Data Ingestion & Parsing | 2-3 days | ✅ Complete |
| **Phase 2** | PostgreSQL Schema & Loading | 2-3 days | ✅ Complete |
| **Phase 3** | SQL Query Tool | 3-4 days | ✅ Complete |
| **Phase 4** | Agent Orchestration | 2-3 days | ✅ Complete |
| **Phase 5** | FastAPI Backend + Analytics | 2-3 days | ✅ Complete |
| **Phase 6** | Streamlit UI + Visualizations | 2-3 days | ✅ Complete |
| **Phase 7** | Authentication & Security | 2-3 days | ✅ Complete |
| **Phase 8** | RAG/Semantic Search | 3-4 days | ✅ Complete |

**Timeline**: 2-3 weeks to working prototype with SQL queries

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- Docker and Docker Compose
- Anthropic API key (for Claude)

### Installation (Docker - Recommended)

1. **Clone repository**
```bash
git clone https://github.com/yourusername/form13f_aiagent.git
cd form13f_aiagent
```

2. **Add your 13F XML files**
```bash
# Place your Form 13F XML files in data/raw/
# See data/raw/README.md for details
cp /path/to/your/filings/*.xml data/raw/
```

3. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your Anthropic API key and DB password
```

4. **Start services with Docker**
```bash
docker-compose up -d
```

5. **Run migrations**
```bash
docker-compose exec api alembic upgrade head
```

6. **Ingest 13F data**
```bash
docker-compose exec api python -m src.ingestion.ingest --folder /app/data/raw
```

7. **Access the application**
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Streamlit UI: http://localhost:8501

### Installation (Local Development with uv)

1. **Clone repository**
```bash
git clone https://github.com/egba4444/form13f_aiagent.git
cd form13f_aiagent
```

2. **Install dependencies with uv** (10x faster than pip)
```bash
# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv sync --all-extras
```

3. **Start PostgreSQL**
```bash
docker-compose up -d postgres
```

4. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your Anthropic API key and DB password
```

5. **Run migrations**
```bash
alembic upgrade head
```

6. **Ingest 13F data**
```bash
python -m src.ingestion.ingest --folder data/raw
```

7. **Start API locally**
```bash
uvicorn src.api.main:app --reload
```

## 🚂 Deployment (Railway)

Deploy to Railway.app in 3 steps:

1. **Push to GitHub**
```bash
git push
```

2. **Connect to Railway**
- Go to https://railway.app/new
- Select "Deploy from GitHub repo"
- Choose `egba4444/form13f_aiagent`

3. **Add Environment Variables**
```bash
DATABASE_URL=postgresql://postgres:...@db...supabase.co:5432/postgres
ANTHROPIC_API_KEY=sk-ant-your-key-here
LLM_PROVIDER=anthropic
LLM_MODEL=claude-3-5-sonnet-20241022
```

**Done!** Your API will be live at `https://your-app.up.railway.app`

See [docs/RAILWAY_DEPLOYMENT.md](docs/RAILWAY_DEPLOYMENT.md) for detailed guide.

## ☁️ Streamlit Cloud Deployment

Deploy the UI to Streamlit Cloud for free:

1. **Push to GitHub** (if not already done)
```bash
git push
```

2. **Deploy to Streamlit Cloud**
- Go to https://share.streamlit.io
- Click "New app"
- Select your repository: `egba4444/form13f_aiagent`
- Set main file path: `src/ui/app.py`
- Click "Deploy"

3. **Configure Environment Variables**
Add in Streamlit Cloud settings:
```bash
API_BASE_URL=https://your-app.up.railway.app
```

**Done!** Your UI will be live at a custom subdomain.

**Production Example**: [https://form13faiagent-ia8jkydleycwabcjzeme4m.streamlit.app/](https://form13faiagent-ia8jkydleycwabcjzeme4m.streamlit.app/)

**Note**: Streamlit Cloud uses `requirements.txt` for dependencies, which is included in the repository.

## 📁 Project Structure

```
form13f_aiagent/
├── README.md
├── pyproject.toml
├── docker-compose.yml
├── .env.example
│
├── docs/
│   ├── ARCHITECTURE.md
│   ├── IMPLEMENTATION_PLAN.md
│   ├── SQL_SCHEMA.md
│   └── DECISIONS.md
│
├── data/
│   ├── raw/              # 13F XML filings (committed to git)
│   ├── processed/        # Parsed data (not tracked)
│   └── cache/            # Temporary cache (not tracked)
│
├── alembic/              # Database migrations
│   └── versions/
│
├── src/
│   ├── agent/            # Claude agent with SQL tool
│   ├── api/              # FastAPI backend
│   ├── db/               # Database layer (SQLAlchemy)
│   ├── ingestion/        # SEC data ingestion
│   ├── models/           # Pydantic data models
│   ├── tools/            # SQL query tool
│   ├── ui/               # Streamlit interface
│   └── utils/
│
├── scripts/
│   ├── download_filings.py
│   └── populate_db.py
│
└── tests/
    ├── unit/
    └── integration/
```

## 🔑 Key Features

### 1. Natural Language to SQL
Claude converts natural language questions into safe SQL queries:

**Input**: "How many AAPL shares did Berkshire hold in Q4 2024?"

**Generated SQL**:
```sql
SELECT h.shares_or_principal, h.value_thousands, f.period_of_report
FROM holdings h
JOIN filings f ON h.accession_number = f.accession_number
WHERE f.cik = '0001067983'
  AND h.ticker = 'AAPL'
  AND f.period_of_report BETWEEN '2024-10-01' AND '2024-12-31'
LIMIT 1;
```

**Answer**: "Berkshire Hathaway held 916,000,000 shares of Apple Inc (AAPL) valued at $157 billion in Q4 2024."

### 2. SQL Safety & Validation
- Read-only queries (SELECT only)
- Query timeout limits (5 seconds)
- Row limits (max 1000 rows)
- SQL injection prevention
- Schema validation

### 3. Database Schema
```sql
-- Core tables
filings       -- Filing metadata (CIK, manager, date, total value)
holdings      -- Individual positions (CUSIP, ticker, shares, value)
issuers       -- Issuer reference data (CUSIP → ticker mapping)
managers      -- Manager reference data (CIK → name mapping)
```

See `docs/SQL_SCHEMA.md` for complete schema.

### 4. Query Examples

| Question | Complexity | Works? |
|----------|------------|--------|
| "How many AAPL shares did Berkshire hold?" | Simple | ✅ |
| "What were Berkshire's top 5 holdings by value?" | Moderate | ✅ |
| "Which managers held more than $1B in TSLA?" | Complex | ✅ |
| "What was the average portfolio value in Q4 2024?" | Analytics | ✅ |
| "Show me all tech holdings across all managers" | Complex | ✅ |

### 5. Interactive Visualizations
The Streamlit UI includes 4 tabs with interactive Plotly visualizations:

**💬 Chat Tab**
- Natural language query interface
- Real-time SQL generation and execution
- CSV export of query results

**📈 Portfolio Explorer**
- Search and select institutional managers
- Portfolio composition charts (pie/bar)
- Key metrics: total value, concentration, holdings count
- Top holdings breakdown with percentages

**🔍 Security Analysis**
- Institutional ownership analysis by CUSIP/ticker
- Top holders visualization
- Ownership concentration metrics (Herfindahl Index)
- Quarter-over-quarter ownership changes

**🚀 Top Movers**
- Biggest portfolio position increases/decreases
- Color-coded charts (green=increase, red=decrease)
- Filter by time period
- Percentage and dollar value changes

All visualizations are:
- Interactive (hover, zoom, pan)
- Responsive (mobile-friendly)
- Cached for performance (5-minute TTL)

### 6. Analytics API Endpoints
FastAPI provides dedicated analytics endpoints:

- `GET /api/v1/analytics/portfolio/{cik}` - Portfolio composition and top holdings
- `GET /api/v1/analytics/security/{cusip}` - Institutional ownership analysis
- `GET /api/v1/analytics/movers` - Biggest position changes across managers
- `GET /api/v1/managers` - Search and list institutional managers

See API docs at `/docs` for full endpoint documentation.

### 7. RAG/Semantic Search (Phase 8 - Completed)
The system includes semantic search over Form 13F filing text:
- Vector database (Qdrant) stores filing text embeddings
- AI-powered semantic search finds relevant sections
- Search manager info, amendments, regulatory disclosures

**Important Limitation:**
Form 13F filings are regulatory documents that report holdings. They typically **do NOT contain**:
- Investment strategies or philosophies
- Investment theses or market commentary
- Future investment plans

Best used for: manager contact info, amendment explanations, fund structure disclosures.
For actual investment analysis, use the SQL query tools instead.

## 📊 Example Usage

### CLI
```bash
# Ask a question
python -m src.agent.cli "How many AAPL shares did Berkshire hold in Q4 2024?"
```

### API
```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What were BlackRock'\''s top 5 holdings?"}'
```

### Python
```python
from src.agent.orchestrator import Agent

agent = Agent()
result = agent.query("How many AAPL shares did Berkshire hold?")

print(result.answer)
print(result.sql_query)  # See generated SQL
print(result.raw_data)   # See query results
```

## 🔧 Configuration

### Environment Variables (.env)
```bash
# Required
ANTHROPIC_API_KEY=your_anthropic_key
DB_PASSWORD=your_secure_password

# Optional
LOG_LEVEL=INFO
ENVIRONMENT=development
```

## 🧪 Testing

```bash
# Run all tests
pytest

# Run unit tests
pytest tests/unit/

# Run integration tests (requires database)
pytest tests/integration/

# Test SQL generation
pytest tests/unit/test_sql_tool.py -v
```

## 📖 Documentation

- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** - System architecture and design decisions
- **[IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md)** - 6-phase roadmap
- **[SQL_SCHEMA.md](docs/SQL_SCHEMA.md)** - Database schema and queries
- **[DECISIONS.md](docs/DECISIONS.md)** - Why SQL-first, why Claude, etc.

## 📈 Performance

- **Query Latency**: < 2 seconds end-to-end
- **SQL Generation**: < 1 second
- **Database Queries**: < 100ms (with proper indexes)
- **Supported Scale**: 100,000+ holdings, 10,000+ filings
- **Concurrent Users**: 50+

## 🤝 Future Enhancements

### Phase 9: Advanced Features
- Real-time data updates (SEC RSS feed)
- Multi-manager comparisons
- Time-series analysis
- Export to Excel/CSV
- Slack/Teams integration

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## 📧 Contact

For questions or feedback, please open an issue.

---

**Status**: ✅ Phases 1-8 Complete - Production Ready
**Architecture**: SQL-First + RAG Semantic Search
**Live Demo**: [Streamlit App](https://form13faiagent-ia8jkydleycwabcjzeme4m.streamlit.app/)

---

Made with Claude 3.5 Sonnet | MIT License
