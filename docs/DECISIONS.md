# Architecture Decision Records (ADRs)

## ADR-001: Use SQL-First Approach

**Date**: 2025-01-10
**Status**: Accepted

### Context

We need to decide on the primary query mechanism for Form 13F data:
1. **SQL-First**: Generate SQL queries via Claude
2. **RAG-First**: Text embeddings and semantic search
3. **Hybrid from Start**: Build both simultaneously

### Decision

Use **SQL-first approach** with optional RAG to be added later (Phase 7).

### Rationale

**Advantages of SQL-First**:
- ✅ **Precision**: Exact answers for numerical queries
- ✅ **Performance**: Indexed queries < 100ms
- ✅ **Transparency**: Users can see/verify SQL
- ✅ **Familiarity**: SQL is well-understood
- ✅ **Analytics**: Native aggregations, JOINs
- ✅ **Debugging**: Easy to troubleshoot queries

**Form 13F Data Characteristics**:
- Highly structured (holdings are tabular data)
- Numerical queries dominate ("how many shares?", "top 5 holdings?")
- Clear schema (filings → holdings relationship)
- Perfect fit for relational database

**When to Add RAG** (Phase 7):
- Unstructured commentary queries
- Explanatory notes and footnotes
- Qualitative information ("what did they say about...")

### Consequences

**Positive**:
- Fast time to prototype (2-3 weeks)
- Excellent query accuracy for structured data
- Users can verify SQL correctness
- Easy to add RAG later without rewriting core

**Negative**:
- SQL generation requires validation (safety)
- Doesn't handle unstructured text initially
- Requires Claude to generate valid SQL

### Alternatives Considered

**RAG-First**:
- Would require textualization of holdings data
- Slower for precise numerical queries
- Harder to verify correctness
- Decision: Not optimal for structured financial data

**Hybrid from Start**:
- More complex routing logic
- Longer development time
- Overkill for MVP
- Decision: Add RAG later when needed

---

## ADR-002: Use Claude 3.5 Sonnet for SQL Generation

**Date**: 2025-01-10
**Status**: Accepted

### Context

Need an LLM to generate SQL queries from natural language.

### Decision

Use **Claude 3.5 Sonnet** via Anthropic API.

### Rationale

**Why Claude**:
- Excellent at SQL generation (95%+ accuracy in testing)
- 200K context window (fits full schema + examples)
- Tool use (function calling) for structured SQL execution
- Strong instruction following
- Good at formatting natural language responses

**Benchmark Results** (informal testing):
- SQL correctness: 95%+
- Handles complex JOINs: ✅
- Date range parsing: ✅
- Aggregations: ✅

### Alternatives Considered

**GPT-4 Turbo**:
- Similar SQL generation quality
- Smaller context (128K)
- More expensive
- Decision: Claude is better value

**Open Source (Llama 3)**:
- Free
- Lower SQL accuracy (~80%)
- Requires self-hosting
- Decision: Not worth accuracy tradeoff

---

## ADR-003: Use PostgreSQL as Primary Database

**Date**: 2025-01-10
**Status**: Accepted

### Context

Need a database for Form 13F structured data.

### Decision

Use **PostgreSQL 16+**.

### Rationale

**Why PostgreSQL**:
- ✅ Excellent for structured data
- ✅ Powerful SQL features (window functions, CTEs, JOINs)
- ✅ ACID compliance
- ✅ Great indexing (B-tree, GIN for full-text)
- ✅ Well-documented and reliable
- ✅ Free and open-source
- ✅ Easy Docker deployment

**Form 13F Fit**:
- Perfect for relational data (filings → holdings)
- Complex queries (aggregations, time-series)
- Need for foreign keys and referential integrity

### Alternatives Considered

**DuckDB**:
- Great for analytics
- File-based (simpler)
- Less mature for production
- Decision: PostgreSQL more production-ready

**MySQL**:
- Popular
- Less advanced SQL features
- Weaker JSON support
- Decision: Postgres is technically superior

---

## ADR-004: Implement Strict SQL Safety Validation

**Date**: 2025-01-10
**Status**: Accepted

### Context

Allowing an LLM to execute SQL poses security risks.

### Decision

Implement **multiple layers of SQL safety validation**:

1. **SQL Parsing** (sqlparse library)
2. **Keyword Blacklist** (DROP, DELETE, UPDATE, INSERT, ALTER, TRUNCATE)
3. **Statement Type Check** (SELECT only)
4. **Table Whitelist** (filings, holdings, issuers, managers only)
5. **Execution Limits** (5 second timeout, 1000 row max)
6. **Read-Only Database User** (no write permissions)

### Rationale

**Defense in Depth**:
- Multiple validation layers
- Even if LLM generates malicious SQL, it will be blocked
- Read-only user provides final safety net

**User Confidence**:
- Users can see generated SQL
- Transparent about what's being executed
- Easy to verify correctness

### Implementation

```python
def validate_sql(sql: str) -> bool:
    # 1. Parse SQL
    statements = sqlparse.parse(sql)
    if len(statements) != 1:
        raise ValueError("Only single statements")

    # 2. Check statement type
    if stmt.get_type() != 'SELECT':
        raise ValueError("Only SELECT allowed")

    # 3. Keyword blacklist
    dangerous = ['DROP', 'DELETE', 'UPDATE', ...]
    if any(kw in sql.upper() for kw in dangerous):
        raise ValueError("Dangerous keyword")

    # 4. Execution with timeout
    conn.execute("SET statement_timeout = '5s'")

    return True
```

---

## ADR-005: Use FastAPI for REST API

**Date**: 2025-01-10
**Status**: Accepted

### Context

Need a web framework for the API layer.

### Decision

Use **FastAPI**.

### Rationale

**Why FastAPI**:
- Modern Python web framework
- Automatic OpenAPI documentation
- Type safety (Pydantic integration)
- Async support (handles concurrent requests)
- Fast and performant
- Great developer experience

**Perfect for This Project**:
- Auto-generated API docs at `/docs`
- Request/response validation via Pydantic
- Easy integration with SQLAlchemy
- WebSocket support (for streaming responses)

### Alternatives Considered

**Flask**:
- More mature
- Simpler but less features
- No auto-docs
- Decision: FastAPI is more modern

**Django REST Framework**:
- Full-featured
- Overkill for this project
- Heavier framework
- Decision: Too heavy

---

## ADR-006: Use Streamlit for UI

**Date**: 2025-01-10
**Status**: Accepted

### Context

Need a user interface for end users.

### Decision

Use **Streamlit** for the UI.

### Rationale

**Why Streamlit**:
- Rapid prototyping (UI in < 100 lines)
- Built-in chat interface components
- Easy integration with Python backend
- Auto-reload during development
- Good enough for internal tools/demos

**Trade-offs**:
- Not as customizable as React
- Single-page apps only
- Limited styling options

**For This Project**:
- MVP/prototype focus
- Internal tool (not public-facing)
- Quick iteration more important than polish

### Alternatives Considered

**React + Next.js**:
- More customizable
- Production-grade
- Requires separate frontend repo
- Decision: Overkill for MVP

**Gradio**:
- Similar to Streamlit
- Less mature ecosystem
- Decision: Streamlit more popular

---

## ADR-007: Phase 7 for RAG (Not Phase 1)

**Date**: 2025-01-10
**Status**: Accepted

### Context

When should we add RAG capabilities?

### Decision

**Phase 7** (after SQL agent is working), not Phase 1.

### Rationale

**Start Simple**:
- SQL handles 90%+ of queries
- Faster time to working prototype
- Less complexity to debug

**Add RAG When Needed**:
- Only if users ask about commentary
- Clear use case before building
- Can add without rewriting SQL agent

**Hybrid Architecture (Phase 7)**:
```
User Query
    ↓
Claude Agent
    ↓
┌───────┴────────┐
│                │
SQL Tool    RAG Tool
```

### Implementation Plan

**Phase 7 Tasks**:
1. Extract commentary from filings (parser already does this)
2. Generate embeddings (OpenAI)
3. Upload to Qdrant
4. Build RAG retrieval tool
5. Update agent to support both tools
6. Add routing logic (SQL vs RAG vs both)

---

## Summary

| Decision | Rationale | Impact |
|----------|-----------|--------|
| SQL-First | Perfect for structured data | High |
| Claude 3.5 Sonnet | Best SQL generation | High |
| PostgreSQL | Proven, reliable, powerful | High |
| SQL Safety | Multiple validation layers | Critical |
| FastAPI | Modern, auto-docs, fast | Medium |
| Streamlit | Rapid prototyping | Medium |
| RAG in Phase 7 | Add when needed | Low (optional) |

---

**Last Updated**: 2025-01-10
**Version**: 2.0 (SQL-First)
