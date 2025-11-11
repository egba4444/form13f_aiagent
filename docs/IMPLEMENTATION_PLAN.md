# Implementation Plan: SQL-First with Optional RAG

## Overview

This document outlines a **6-phase implementation plan** for building a SQL-first Form 13F AI Agent, with Phase 7 reserved for optionally adding RAG capabilities for unstructured commentary.

**Total Timeline**: 2-3 weeks to working SQL-based prototype

---

## Phase 1: Data Ingestion & Parsing (2-3 days)

### Goal
Download Form 13F filings from SEC EDGAR and parse XML into structured Python objects.

###Tasks

#### 1.1 SEC EDGAR Client (Day 1)
**File**: `src/ingestion/edgar_client.py`

- [ ] Implement `SECEdgarClient` class with async HTTP
- [ ] Rate limiting (10 req/sec) using asyncio
- [ ] Retry logic with exponential backoff (tenacity)
- [ ] Method: `search_filings()` - Search by CIK/date range
- [ ] Method: `download_filing()` - Download specific filing
- [ ] Method: `get_latest_filings()` - RSS feed polling
- [ ] Local caching to avoid re-downloads
- [ ] Unit tests with mock SEC responses

**Key Difference from RAG approach**: Same component, but no textualization needed downstream.

#### 1.2 XML Parser (Day 1-2)
**File**: `src/ingestion/parser.py`

- [ ] Implement `Form13FParser` class using lxml
- [ ] Method: `parse()` - Main entry point
- [ ] Method: `_parse_metadata()` - Extract filing metadata
- [ ] Method: `_parse_holdings()` - Extract holdings from information table
- [ ] Method: `_extract_commentary()` - Extract explanatory notes (for Phase 7)
- [ ] Handle multiple XML schema versions (1.6, 1.7)
- [ ] CUSIP validation (format + check digit)
- [ ] Unit tests with sample XML files

#### 1.3 Reference Data Integration (Day 2)
**File**: `src/ingestion/reference_data.py`

- [ ] Implement `CUSIPResolver` class
- [ ] OpenFIGI API integration for CUSIP → Ticker
- [ ] Local cache (SQLite or in-memory)
- [ ] Batch resolution for efficiency
- [ ] Error handling for unknown CUSIPs
- [ ] Unit tests

#### 1.4 Data Models (Day 2)
**Files**: `src/models/*.py`

- [ ] `filing.py`:
  - `FilingMetadata` - Pydantic model for filing
  - `ParsedFiling` - Complete parsed filing
- [ ] `holding.py`:
  - `HoldingRecord` - Individual position
- [ ] Validation logic (CUSIP format, date ranges)
- [ ] Serialization to/from JSON
- [ ] Unit tests

#### 1.5 Download Script (Day 3)
**File**: `scripts/download_filings.py`

- [ ] CLI script with argparse
- [ ] Arguments: --ciks, --quarters, --output-dir
- [ ] Download specified filings
- [ ] Parse and save to JSON
- [ ] Progress bar (tqdm)
- [ ] Example usage docs

### Deliverables
- [ ] SEC EDGAR client with rate limiting
- [ ] XML parser handling multiple schemas
- [ ] Pydantic data models
- [ ] Sample data downloaded (10-20 filings)
- [ ] Unit tests (>80% coverage)

### Success Criteria
- ✅ Can download 100 filings without errors
- ✅ Parser handles different XML schemas
- ✅ All fields mapped correctly to models
- ✅ Ticker resolution works for 95%+ of holdings

---

## Phase 2: PostgreSQL Schema & Loading (2-3 days)

### Goal
Create PostgreSQL database schema and load parsed data.

### Tasks

#### 2.1 Database Schema (Day 1)
**File**: `alembic/versions/001_initial_schema.py`

- [ ] Set up Alembic for migrations
- [ ] Create `filings` table
- [ ] Create `holdings` table with foreign key
- [ ] Create `issuers` reference table
- [ ] Create `managers` reference table
- [ ] Add indexes for common queries:
  - `idx_holdings_ticker`
  - `idx_holdings_cusip`
  - `idx_filings_cik`
  - `idx_filings_date`
  - `idx_filings_cik_date` (composite)
- [ ] Test migration up/down

#### 2.2 SQLAlchemy Models (Day 1)
**File**: `src/db/models.py`

- [ ] `Filing` ORM model
- [ ] `Holding` ORM model
- [ ] `Issuer` ORM model
- [ ] `Manager` ORM model
- [ ] Relationships (filing → holdings)
- [ ] Unit tests for models

#### 2.3 Repository Layer (Day 2)
**File**: `src/db/repositories.py`

- [ ] `FilingRepository`:
  - `create()` - Insert filing
  - `get_by_accession()` - Retrieve filing
  - `list_by_cik()` - List manager's filings
  - `list_by_date_range()` - Filter by date
- [ ] `HoldingRepository`:
  - `bulk_create()` - Efficient batch insert
  - `get_by_ticker()` - Holdings for specific security
- [ ] `ManagerRepository`:
  - `upsert()` - Insert or update manager info
- [ ] `IssuerRepository`:
  - `upsert()` - Insert or update issuer info
- [ ] Connection pooling
- [ ] Transaction management
- [ ] Unit tests with test database

#### 2.4 Data Loading Script (Day 2-3)
**File**: `scripts/populate_db.py`

- [ ] Read JSON files from `data/processed/`
- [ ] Load filings into database
- [ ] Load holdings (bulk insert for performance)
- [ ] Update managers table
- [ ] Update issuers table
- [ ] Deduplication logic (ON CONFLICT DO UPDATE)
- [ ] Progress tracking
- [ ] Validation (check all data loaded correctly)

#### 2.5 Docker Setup (Day 3)
**File**: `docker-compose.yml`

- [ ] PostgreSQL service configuration
- [ ] Environment variables
- [ ] Persistent volume for data
- [ ] Health check
- [ ] Network configuration
- [ ] README instructions

### Deliverables
- [ ] Alembic migrations
- [ ] SQLAlchemy ORM models
- [ ] Repository classes
- [ ] Data loading script
- [ ] Docker Compose file
- [ ] Sample database with 100+ filings

### Success Criteria
- ✅ Can load 1000+ filings without errors
- ✅ Query performance < 100ms for single manager
- ✅ No duplicate data
- ✅ All foreign keys working
- ✅ Indexes improve query speed (verified with EXPLAIN)

---

## Phase 3: SQL Query Tool (3-4 days)

### Goal
Build tool that allows Claude to generate and execute safe SQL queries.

### Tasks

#### 3.1 SQL Tool Core (Day 1-2)
**File**: `src/tools/sql_tool.py`

- [ ] Implement `SQLQueryTool` class
- [ ] Method: `get_tool_definition()` - Tool schema for Claude
- [ ] Method: `execute()` - Execute SQL safely
- [ ] Method: `_validate_sql()` - Safety checks
- [ ] Method: `_load_schema()` - Database schema as string
- [ ] SQL parsing using sqlparse library
- [ ] Safety validation:
  - Only SELECT statements
  - No DROP/DELETE/UPDATE/INSERT
  - No multiple statements
  - Table whitelist
- [ ] Execution limits:
  - 5 second timeout
  - Max 1000 rows
  - Automatic LIMIT injection
- [ ] Result formatting
- [ ] Unit tests with safe/unsafe SQL examples

#### 3.2 SQL Validation (Day 2)
**File**: `src/tools/sql_validator.py`

- [ ] SQL parsing and AST analysis
- [ ] Keyword blacklist enforcement
- [ ] Table/column whitelist verification
- [ ] Detect SQL injection patterns
- [ ] Comprehensive test suite

#### 3.3 Schema Documentation (Day 3)
**File**: `src/tools/schema_loader.py`

- [ ] Load schema from database dynamically
- [ ] Format schema for Claude (with descriptions)
- [ ] Include sample queries
- [ ] Foreign key relationships
- [ ] Common JOIN patterns
- [ ] Update when schema changes

#### 3.4 Example Queries (Day 3-4)
**File**: `examples/sql_queries.json`

- [ ] Create 20+ example Q&A pairs:
  - "How many shares?" → Simple SELECT
  - "Top 5 holdings?" → ORDER BY + LIMIT
  - "Managers holding X?" → JOIN + WHERE
  - "Total value?" → SUM aggregation
  - "Average position?" → AVG aggregation
- [ ] Annotate with SQL + expected results
- [ ] Use for testing and prompt engineering

### Deliverables
- [ ] SQL query tool with safety validation
- [ ] Comprehensive test suite
- [ ] Schema documentation for Claude
- [ ] Example queries

### Success Criteria
- ✅ Blocks all unsafe SQL (100% in test suite)
- ✅ Executes safe SQL correctly (95%+ accuracy)
- ✅ Query timeout works
- ✅ Row limits enforced
- ✅ Clear error messages

---

## Phase 4: Agent Orchestration (2-3 days)

### Goal
Build Claude agent that uses SQL tool to answer questions.

### Tasks

#### 4.1 Agent Core (Day 1-2)
**File**: `src/agent/orchestrator.py`

- [ ] Implement `Agent` class
- [ ] Integration with Anthropic API (Claude 3.5 Sonnet)
- [ ] Method: `query()` - Main entry point
- [ ] Tool use handling (function calling)
- [ ] System prompt with database schema
- [ ] Response formatting
- [ ] Error handling
- [ ] Conversation memory (last 5 exchanges)
- [ ] Unit tests with mock Claude API

#### 4.2 System Prompts (Day 2)
**File**: `src/agent/prompts.py`

- [ ] Main system prompt for SQL generation
- [ ] Few-shot examples for complex queries
- [ ] Prompt for formatting numbers
- [ ] Prompt for handling errors
- [ ] Prompt for citing sources
- [ ] Version management (A/B testing)

#### 4.3 Response Formatter (Day 2-3)
**File**: `src/agent/formatter.py`

- [ ] Format SQL results as natural language
- [ ] Number formatting (1000000 → "1 million")
- [ ] Currency formatting ($1500000 → "$1.5M")
- [ ] Date formatting
- [ ] Table formatting (for multiple rows)

#### 4.4 Integration Tests (Day 3)
**File**: `tests/integration/test_agent.py`

- [ ] End-to-end tests with real database
- [ ] Test suite of 30+ Q&A pairs
- [ ] Measure accuracy (target: 90%+)
- [ ] Measure latency (target: < 2s)
- [ ] Edge case handling

### Deliverables
- [ ] Agent orchestrator
- [ ] System prompts optimized for SQL
- [ ] Response formatter
- [ ] Integration test suite

### Success Criteria
- ✅ Answer accuracy > 90%
- ✅ SQL generation accuracy > 95%
- ✅ End-to-end latency < 2 seconds
- ✅ Proper error handling
- ✅ Good number formatting

---

## Phase 5: FastAPI Backend (2-3 days)

### Goal
Build production-ready REST API.

### Tasks

#### 5.1 API Core (Day 1)
**File**: `src/api/main.py`

- [ ] FastAPI application setup
- [ ] CORS middleware
- [ ] Error handlers
- [ ] Request/response logging
- [ ] Startup/shutdown events
- [ ] Health check endpoint

#### 5.2 Query Router (Day 1-2)
**File**: `src/api/routers/query.py`

- [ ] POST `/api/v1/query` - Submit question
- [ ] Request validation (Pydantic)
- [ ] Response model with answer + SQL + data
- [ ] Optional fields (include_sql, include_raw_data)
- [ ] Rate limiting (slowapi)
- [ ] Unit tests

#### 5.3 Data Routers (Day 2)
**File**: `src/api/routers/filings.py`, `routers/holdings.py`

- [ ] GET `/api/v1/filings` - List filings
- [ ] GET `/api/v1/filings/{accession}` - Get specific filing
- [ ] GET `/api/v1/holdings` - Browse holdings
- [ ] GET `/api/v1/managers` - List managers
- [ ] Pagination support
- [ ] Filtering (by CIK, ticker, date)
- [ ] Unit tests

#### 5.4 Dependency Injection (Day 2-3)
**File**: `src/api/dependencies.py`

- [ ] Database session dependency
- [ ] Agent dependency
- [ ] SQL tool dependency
- [ ] Configuration dependency

#### 5.5 API Documentation (Day 3)
- [ ] OpenAPI schema (auto-generated)
- [ ] Example requests/responses
- [ ] Authentication docs (if added)
- [ ] Rate limit docs

### Deliverables
- [ ] FastAPI application
- [ ] 6+ REST endpoints
- [ ] Request/response validation
- [ ] API documentation at /docs
- [ ] Unit and integration tests

### Success Criteria
- ✅ All endpoints working
- ✅ OpenAPI docs complete
- ✅ Rate limiting functional
- ✅ Error responses informative
- ✅ Performance < 2s per query

---

## Phase 6: Streamlit UI (2-3 days)

### Goal
Build user-friendly interface for asking questions.

### Tasks

#### 6.1 Main Interface (Day 1-2)
**File**: `src/ui/streamlit_app.py`

- [ ] Chat interface with message history
- [ ] Text input for queries
- [ ] Display answers with formatting
- [ ] Show generated SQL (toggle)
- [ ] Show raw data in table
- [ ] Session state management
- [ ] Loading indicators

#### 6.2 Sidebar & Filters (Day 2)
- [ ] Manager selection dropdown
- [ ] Ticker filter
- [ ] Date range picker
- [ ] Settings:
  - Show SQL toggle
  - Show raw data toggle
  - API key input (if needed)

#### 6.3 Visualizations (Day 2-3)
- [ ] Holdings pie chart (top 10)
- [ ] Portfolio value over time
- [ ] Position changes (waterfall chart)
- [ ] Integration with Plotly

#### 6.4 Export & History (Day 3)
- [ ] Export conversation to PDF
- [ ] Download SQL results as CSV
- [ ] Query history (last 20)
- [ ] Save/load sessions

### Deliverables
- [ ] Streamlit application
- [ ] Chat interface
- [ ] Filters and settings
- [ ] Visualizations
- [ ] Export functionality

### Success Criteria
- ✅ Intuitive UX
- ✅ Fast perceived performance
- ✅ Mobile-friendly
- ✅ Accessible at localhost:8501

---

## Phase 7: Optional RAG for Commentary (3-4 days)

**Status**: Future enhancement

### When to Implement
Add RAG when you need to answer questions about unstructured text:
- "What commentary did BlackRock provide about derivatives?"
- "What did Vanguard say about risk factors?"
- "Show me explanatory notes for unusual positions"

### Tasks

#### 7.1 Vector Store Setup (Day 1)
- [ ] Docker Compose for Qdrant
- [ ] Collection creation
- [ ] Metadata schema design

#### 7.2 Commentary Extraction & Embedding (Day 2)
- [ ] Extract commentary from filings (already in parser)
- [ ] Chunk commentary text
- [ ] Generate embeddings (OpenAI)
- [ ] Upload to Qdrant with metadata

#### 7.3 RAG Retrieval Tool (Day 2-3)
- [ ] Implement retrieval logic
- [ ] Semantic search
- [ ] Metadata filtering
- [ ] Context formatting for Claude

#### 7.4 Hybrid Agent (Day 3-4)
- [ ] Update agent to support both tools
- [ ] Routing logic (SQL vs RAG vs both)
- [ ] Synthesize responses from multiple sources

### Deliverables
- [ ] Qdrant vector store
- [ ] Commentary embeddings
- [ ] RAG retrieval tool
- [ ] Updated agent with dual tools

---

## Development Progression

### Weeks 1-2: Prototype
- [ ] Complete Phases 1-3
- [ ] Working SQL agent (CLI only)
- [ ] Sample data (100 filings)
- [ ] Manual testing

### Week 3: Alpha
- [ ] Complete Phases 4-5
- [ ] FastAPI backend
- [ ] Basic Streamlit UI
- [ ] Automated tests

### Week 4: Beta
- [ ] Complete Phase 6
- [ ] Full UI with visualizations
- [ ] Scale to 1000+ filings
- [ ] Performance optimization

### Week 5+ (Optional): Add RAG
- [ ] Phase 7 if needed
- [ ] Hybrid SQL+RAG agent

---

## Testing Strategy

### Unit Tests
- Each module has ≥80% coverage
- Mock external dependencies (SEC API, Claude API)
- Fast execution (< 30 seconds total)

### Integration Tests
- End-to-end query flow
- Real database (test instance)
- Real SQL execution
- Mock Claude API or use real with test key
- Test suite of 50+ Q&A pairs

### Performance Tests
- Load testing (100 concurrent queries)
- Database query benchmarks
- API latency measurement
- Memory profiling

### Manual Tests
- UI/UX testing
- Edge case exploration
- Real user queries
- Feedback collection

---

## Risk Mitigation

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Claude generates invalid SQL | High | Medium | Robust validation, fallback error messages |
| SQL injection | Critical | Low | Strict parsing, whitelist, read-only user |
| Database performance | Medium | Medium | Proper indexes, query optimization |
| SEC API rate limits | Medium | Low | Caching, queue, respect limits |
| Claude API costs | Low | Low | Token tracking, caching responses |

---

## Success Metrics

### Phase 1-3 (Data & SQL Tool)
- ✅ 1000+ filings in database
- ✅ SQL tool blocks 100% of unsafe queries
- ✅ SQL generation accuracy > 95%

### Phase 4-5 (Agent & API)
- ✅ Answer accuracy > 90%
- ✅ End-to-end latency < 2 seconds
- ✅ API uptime > 99%

### Phase 6 (UI)
- ✅ UI load time < 1 second
- ✅ User satisfaction > 4/5
- ✅ Mobile-friendly

### Phase 7 (Optional RAG)
- ✅ Retrieval accuracy > 85%
- ✅ Hybrid routing works correctly
- ✅ Latency < 3 seconds

---

**Last Updated**: 2025-01-10
**Version**: 2.0 (SQL-First)
**Status**: Phase 1 Ready to Start
