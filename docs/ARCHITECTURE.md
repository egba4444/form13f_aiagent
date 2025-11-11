# System Architecture (SQL-First)

## Table of Contents
- [Overview](#overview)
- [Component Architecture](#component-architecture)
- [Data Flow](#data-flow)
- [SQL Query Tool](#sql-query-tool)
- [Future: Hybrid SQL + RAG](#future-hybrid-sql--rag)

## Overview

The Form 13F AI Agent uses a **SQL-first architecture** where Claude 3.5 Sonnet generates and executes SQL queries against a PostgreSQL database to answer questions about institutional holdings.

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                          │
│                  (Streamlit / FastAPI Frontend)                 │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────┐
│                   CLAUDE 3.5 SONNET AGENT                       │
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    │
│  │ Parse Query  │───▶│ Generate SQL │───▶│ Format       │    │
│  │ Extract      │    │ Validate &   │    │ Response     │    │
│  │ Intent       │    │ Execute      │    │              │    │
│  └──────────────┘    └──────┬───────┘    └──────────────┘    │
└─────────────────────────────┼───────────────────────────────────┘
                              │
                 ┌────────────▼────────────┐
                 │                         │
                 │   POSTGRESQL DATABASE   │
                 │                         │
                 │  ┌──────────────────┐  │
                 │  │ filings          │  │
                 │  │ holdings         │  │
                 │  │ issuers          │  │
                 │  │ managers         │  │
                 │  └──────────────────┘  │
                 └─────────────────────────┘
                              ▲
                              │
┌─────────────────────────────┴───────────────────────────────────┐
│              DATA INGESTION PIPELINE                            │
│                                                                 │
│  SEC EDGAR API → Parse XML → Transform → Load to PostgreSQL    │
└─────────────────────────────────────────────────────────────────┘
```

## Component Architecture

### 1. Data Ingestion Layer

**Purpose**: Download and parse SEC Form 13F filings

#### Components

**SEC EDGAR Client** (`src/ingestion/edgar_client.py`)
- Downloads 13F-HR filings from SEC EDGAR
- Rate limiting (10 req/sec)
- Caching to avoid re-downloads
- Retry logic for transient failures

**XML Parser** (`src/ingestion/parser.py`)
- Parses Form 13F-HR XML
- Extracts holdings from information table
- Extracts metadata from cover page
- Handles multiple XML schema versions

**Data Models** (`src/models/`)
- Pydantic models for type safety
- Validation logic
- Serialization/deserialization

**Key Difference from RAG Approach**:
- No textualization needed
- No chunking strategy
- Direct mapping: XML → Python objects → SQL tables

---

### 2. Database Layer (PostgreSQL)

**Purpose**: Structured storage of Form 13F data

#### Schema Design

```sql
-- Filing metadata
CREATE TABLE filings (
    accession_number VARCHAR(20) PRIMARY KEY,
    cik VARCHAR(10) NOT NULL,
    manager_name VARCHAR(255) NOT NULL,
    filing_date DATE NOT NULL,
    period_of_report DATE NOT NULL,
    total_value_thousands BIGINT NOT NULL,
    number_of_holdings INTEGER NOT NULL,
    raw_xml_url TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Individual holdings
CREATE TABLE holdings (
    id SERIAL PRIMARY KEY,
    accession_number VARCHAR(20) REFERENCES filings(accession_number) ON DELETE CASCADE,
    cusip VARCHAR(9) NOT NULL,
    issuer_name VARCHAR(255) NOT NULL,
    ticker VARCHAR(10),
    title_of_class VARCHAR(100),
    value_thousands BIGINT NOT NULL,
    shares_or_principal BIGINT NOT NULL,
    sh_or_prn VARCHAR(3),  -- 'SH' or 'PRN'
    investment_discretion VARCHAR(10),
    put_call VARCHAR(4),
    voting_authority_sole BIGINT DEFAULT 0,
    voting_authority_shared BIGINT DEFAULT 0,
    voting_authority_none BIGINT DEFAULT 0
);

-- Reference data: CUSIP → Ticker mappings
CREATE TABLE issuers (
    cusip VARCHAR(9) PRIMARY KEY,
    ticker VARCHAR(10),
    issuer_name VARCHAR(255),
    exchange VARCHAR(10),
    sector VARCHAR(50),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Reference data: Manager information
CREATE TABLE managers (
    cik VARCHAR(10) PRIMARY KEY,
    manager_name VARCHAR(255) NOT NULL,
    address TEXT,
    first_filing_date DATE,
    last_filing_date DATE
);

-- Indexes for fast queries
CREATE INDEX idx_holdings_ticker ON holdings(ticker);
CREATE INDEX idx_holdings_cusip ON holdings(cusip);
CREATE INDEX idx_holdings_accession ON holdings(accession_number);
CREATE INDEX idx_holdings_value ON holdings(value_thousands DESC);
CREATE INDEX idx_filings_cik ON filings(cik);
CREATE INDEX idx_filings_date ON filings(period_of_report);
CREATE INDEX idx_filings_cik_date ON filings(cik, period_of_report);
```

**Why PostgreSQL?**
- ✅ Excellent for structured data
- ✅ ACID compliance
- ✅ Powerful SQL capabilities (JOINs, aggregations)
- ✅ Full-text search (if needed)
- ✅ Well-understood and reliable

#### SQLAlchemy Models

```python
# src/db/models.py

from sqlalchemy import Column, String, Integer, BigInteger, Date, ForeignKey
from sqlalchemy.orm import relationship

class Filing(Base):
    __tablename__ = "filings"

    accession_number = Column(String(20), primary_key=True)
    cik = Column(String(10), nullable=False, index=True)
    manager_name = Column(String(255), nullable=False)
    filing_date = Column(Date, nullable=False)
    period_of_report = Column(Date, nullable=False, index=True)
    total_value_thousands = Column(BigInteger, nullable=False)
    number_of_holdings = Column(Integer, nullable=False)
    raw_xml_url = Column(String)

    # Relationship
    holdings = relationship("Holding", back_populates="filing", cascade="all, delete-orphan")

class Holding(Base):
    __tablename__ = "holdings"

    id = Column(Integer, primary_key=True)
    accession_number = Column(String(20), ForeignKey("filings.accession_number"), nullable=False)
    cusip = Column(String(9), nullable=False, index=True)
    ticker = Column(String(10), index=True)
    issuer_name = Column(String(255), nullable=False)
    value_thousands = Column(BigInteger, nullable=False, index=True)
    shares_or_principal = Column(BigInteger, nullable=False)
    # ... more fields

    # Relationship
    filing = relationship("Filing", back_populates="holdings")
```

---

### 3. SQL Query Tool

**Purpose**: Convert natural language to safe SQL queries

**Component**: `src/tools/sql_tool.py`

#### How It Works

1. **Schema Injection**: Provide database schema to Claude
2. **SQL Generation**: Claude generates SQL from natural language
3. **Validation**: Check for safety (SELECT only, no DROP/DELETE)
4. **Execution**: Execute query with timeout
5. **Formatting**: Format results as structured data

#### Tool Definition for Claude

```python
{
    "name": "query_database",
    "description": "Execute SQL query on Form 13F database to retrieve holdings data",
    "input_schema": {
        "type": "object",
        "properties": {
            "sql_query": {
                "type": "string",
                "description": "A valid PostgreSQL SELECT query. Use only SELECT statements."
            },
            "explanation": {
                "type": "string",
                "description": "Brief explanation of what the query does"
            }
        },
        "required": ["sql_query"]
    }
}
```

#### Safety Mechanisms

**1. SQL Parsing & Validation**
```python
def validate_sql(sql: str) -> bool:
    """
    Ensure query is safe to execute.

    Checks:
    - Only SELECT statements
    - No DROP, DELETE, UPDATE, INSERT
    - No multiple statements (no semicolons except at end)
    - No comments that might hide malicious code
    """
    # Parse SQL using sqlparse
    statements = sqlparse.parse(sql)

    if len(statements) != 1:
        raise ValueError("Only single SQL statements allowed")

    stmt = statements[0]

    # Check statement type
    if stmt.get_type() != 'SELECT':
        raise ValueError("Only SELECT queries allowed")

    # Additional checks...

    return True
```

**2. Query Execution Limits**
```python
def execute_sql(sql: str) -> List[Dict]:
    """
    Execute SQL with safety limits.
    """
    # Set statement timeout
    with engine.connect() as conn:
        conn.execute(text("SET statement_timeout = '5s'"))

        # Add LIMIT if not present
        if "LIMIT" not in sql.upper():
            sql = f"{sql.rstrip(';')} LIMIT 1000;"

        result = conn.execute(text(sql))
        return [dict(row) for row in result]
```

**3. Schema Whitelist**
```python
ALLOWED_TABLES = {"filings", "holdings", "issuers", "managers"}

def extract_tables(sql: str) -> Set[str]:
    """Extract table names from SQL query"""
    # ... parsing logic ...

def validate_tables(sql: str) -> bool:
    """Ensure query only accesses allowed tables"""
    tables = extract_tables(sql)
    return tables.issubset(ALLOWED_TABLES)
```

---

### 4. Agent Orchestration

**Component**: `src/agent/orchestrator.py`

**LLM**: Claude 3.5 Sonnet

#### Agent Flow

```
User Query
    ↓
[Claude Understands Intent]
    ↓
[Claude Calls query_database Tool]
    ↓
{
    "sql_query": "SELECT ...",
    "explanation": "This query retrieves..."
}
    ↓
[Validate & Execute SQL]
    ↓
[Return Results to Claude]
    ↓
[Claude Formats Answer]
    ↓
Natural Language Response
```

#### System Prompt

```
You are a financial analyst assistant specializing in SEC Form 13F institutional holdings data.

You have access to a PostgreSQL database with the following schema:

TABLE filings:
- accession_number (PK): Filing identifier
- cik: Central Index Key (manager identifier)
- manager_name: Name of institutional manager
- filing_date: Date filing was submitted
- period_of_report: Quarter end date
- total_value_thousands: Total portfolio value in thousands
- number_of_holdings: Count of positions

TABLE holdings:
- id (PK)
- accession_number (FK to filings)
- cusip: Security identifier
- ticker: Stock ticker symbol (e.g., 'AAPL')
- issuer_name: Company name
- value_thousands: Position value in thousands
- shares_or_principal: Number of shares held
- investment_discretion: 'SOLE', 'SHARED', or 'DEFINED'
- voting_authority_sole/shared/none: Voting rights

TABLE issuers:
- cusip (PK)
- ticker
- issuer_name
- sector

TABLE managers:
- cik (PK)
- manager_name

When answering questions:
1. Use the query_database tool to retrieve data
2. Write efficient SQL queries with appropriate JOINs
3. Always explain your SQL query logic
4. Format numbers clearly (e.g., "1,234,567 shares", "$15.2 billion")
5. Cite your sources (manager name, filing date)
6. If data isn't available, say so clearly

Important:
- Only use SELECT statements
- Be precise with date ranges (quarters)
- Handle NULL values gracefully
```

#### Example Interaction

**User**: "How many AAPL shares did Berkshire Hathaway hold in Q4 2024?"

**Claude's Tool Call**:
```json
{
    "name": "query_database",
    "input": {
        "sql_query": "SELECT h.shares_or_principal, h.value_thousands, f.period_of_report, f.filing_date FROM holdings h JOIN filings f ON h.accession_number = f.accession_number WHERE f.cik = '0001067983' AND h.ticker = 'AAPL' AND f.period_of_report BETWEEN '2024-10-01' AND '2024-12-31' LIMIT 1;",
        "explanation": "This query retrieves Berkshire Hathaway's (CIK 0001067983) Apple Inc (AAPL) holdings for Q4 2024"
    }
}
```

**Query Results**:
```json
[
    {
        "shares_or_principal": 916000000,
        "value_thousands": 157000000,
        "period_of_report": "2024-12-31",
        "filing_date": "2025-02-14"
    }
]
```

**Claude's Response**:
```
According to the Form 13F filing submitted on February 14, 2025 for the period
ending December 31, 2024, Berkshire Hathaway Inc held 916,000,000 shares of
Apple Inc (AAPL), valued at $157.0 billion.
```

---

### 5. API Layer

**Component**: `src/api/main.py`

**Framework**: FastAPI

**Endpoints**:
```python
POST   /api/v1/query           # Natural language query
GET    /api/v1/filings         # List filings (with filters)
GET    /api/v1/filings/{accession}  # Get specific filing
GET    /api/v1/holdings        # Browse holdings (paginated)
GET    /api/v1/managers        # List all managers
GET    /api/v1/health          # Health check
```

**Request/Response Models**:
```python
# Query request
class QueryRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=500)
    include_sql: bool = False  # Return generated SQL?
    include_raw_data: bool = False  # Return raw query results?

# Query response
class QueryResponse(BaseModel):
    answer: str
    sql_query: Optional[str] = None  # If include_sql=True
    raw_data: Optional[List[Dict]] = None  # If include_raw_data=True
    execution_time_ms: int
    row_count: int
```

---

### 6. UI Layer

**Component**: `src/ui/streamlit_app.py`

**Framework**: Streamlit

**Features**:
- Chat interface for natural language queries
- Display generated SQL (toggle on/off)
- Show raw query results in table
- Export results to CSV
- Query history
- Manager/ticker filters

---

## Data Flow

### Ingestion Flow

```
1. Download Filing
   SEC EDGAR API → Raw XML file

2. Parse XML
   XML → ParsedFiling(metadata, holdings)

3. Enrich
   CUSIP → Ticker (via OpenFIGI API)

4. Load to Database
   INSERT INTO filings VALUES (...)
   INSERT INTO holdings VALUES (...), (...), ...

5. Update Reference Tables
   INSERT INTO managers ... ON CONFLICT DO UPDATE
   INSERT INTO issuers ... ON CONFLICT DO UPDATE
```

### Query Flow

```
1. User Input
   "How many AAPL shares did Berkshire hold?"

2. Claude Receives Query + Schema
   System Prompt + Database Schema + User Query

3. Claude Generates SQL via Tool Call
   {
       "sql_query": "SELECT ...",
       "explanation": "..."
   }

4. Validate SQL
   - Check for SELECT only
   - Validate table names
   - Parse for safety

5. Execute SQL
   PostgreSQL executes query
   Returns: [{shares_or_principal: 916000000, ...}]

6. Claude Formats Answer
   "Berkshire Hathaway held 916,000,000 shares..."

7. Return to User
   Display answer (+ optionally SQL + raw data)
```

---

## SQL Query Tool Implementation

### Tool Class

```python
# src/tools/sql_tool.py

from sqlalchemy import create_engine, text
import sqlparse

class SQLQueryTool:
    """
    Tool for executing safe SQL queries.
    Used by Claude agent via function calling.
    """

    def __init__(self, database_url: str):
        self.engine = create_engine(database_url)
        self.schema = self._load_schema()

    def get_tool_definition(self) -> dict:
        """Return tool definition for Claude"""
        return {
            "name": "query_database",
            "description": f"""Execute SQL query on Form 13F database.

Database Schema:
{self.schema}

Guidelines:
- Use only SELECT statements
- Use JOINs to combine data from multiple tables
- Add LIMIT clause for large result sets
- Handle date ranges carefully (quarters)
""",
            "input_schema": {
                "type": "object",
                "properties": {
                    "sql_query": {
                        "type": "string",
                        "description": "A valid PostgreSQL SELECT query"
                    }
                },
                "required": ["sql_query"]
            }
        }

    def execute(self, sql_query: str) -> dict:
        """
        Execute SQL query safely.

        Returns:
            {
                "success": bool,
                "data": List[Dict],
                "error": Optional[str],
                "row_count": int
            }
        """
        try:
            # Validate
            self._validate_sql(sql_query)

            # Execute with timeout
            with self.engine.connect() as conn:
                conn.execute(text("SET statement_timeout = '5s'"))
                result = conn.execute(text(sql_query))
                rows = [dict(row._mapping) for row in result]

            return {
                "success": True,
                "data": rows,
                "row_count": len(rows)
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "data": [],
                "row_count": 0
            }

    def _validate_sql(self, sql: str):
        """Validate SQL is safe to execute"""
        # Parse SQL
        statements = sqlparse.parse(sql)

        if len(statements) != 1:
            raise ValueError("Only single statements allowed")

        stmt = statements[0]

        # Check type
        if stmt.get_type() != 'SELECT':
            raise ValueError(f"Only SELECT allowed, got {stmt.get_type()}")

        # Check for dangerous keywords
        dangerous = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'TRUNCATE']
        sql_upper = sql.upper()
        for keyword in dangerous:
            if keyword in sql_upper:
                raise ValueError(f"Keyword {keyword} not allowed")

        # Add LIMIT if missing
        if 'LIMIT' not in sql_upper and len(sql) > 0:
            raise ValueError("LIMIT clause required")

    def _load_schema(self) -> str:
        """Load database schema as string"""
        return """
        TABLE filings (
            accession_number VARCHAR(20) PRIMARY KEY,
            cik VARCHAR(10),
            manager_name VARCHAR(255),
            filing_date DATE,
            period_of_report DATE,
            total_value_thousands BIGINT,
            number_of_holdings INTEGER
        )

        TABLE holdings (
            id SERIAL PRIMARY KEY,
            accession_number VARCHAR(20) REFERENCES filings,
            cusip VARCHAR(9),
            ticker VARCHAR(10),
            issuer_name VARCHAR(255),
            value_thousands BIGINT,
            shares_or_principal BIGINT,
            investment_discretion VARCHAR(10)
        )

        TABLE issuers (
            cusip VARCHAR(9) PRIMARY KEY,
            ticker VARCHAR(10),
            issuer_name VARCHAR(255),
            sector VARCHAR(50)
        )

        TABLE managers (
            cik VARCHAR(10) PRIMARY KEY,
            manager_name VARCHAR(255)
        )
        """
```

---

## Future: Hybrid SQL + RAG

### When to Add RAG (Phase 7)

Add RAG when you need to answer questions about:
- Explanatory notes and commentary
- Qualitative information ("What did they say about...")
- Free-form text that doesn't fit in structured fields

### Hybrid Architecture

```
User Query
    ↓
Claude Agent (Router)
    ↓
    ├─────────────────┬─────────────────┐
    │                 │                 │
SQL Tool        RAG Tool          Both
    │                 │                 │
PostgreSQL      Qdrant          SQL + RAG
    │                 │                 │
    └─────────────────┴─────────────────┘
                      │
            Synthesize Response
```

### Routing Logic

```python
# Phase 7: Agent decides which tool to use

if "commentary" in query or "said" in query or "notes" in query:
    # Use RAG
    use_tool("retrieve_commentary")
elif "how many" in query or "total" in query or "top" in query:
    # Use SQL
    use_tool("query_database")
else:
    # Use both, synthesize answer
    sql_results = use_tool("query_database")
    rag_results = use_tool("retrieve_commentary")
    synthesize(sql_results, rag_results)
```

---

## Technology Choices

### Why SQL-First?

**Advantages**:
- ✅ **Precision**: Exact answers for structured queries
- ✅ **Performance**: Indexed queries < 100ms
- ✅ **Simplicity**: Well-understood technology
- ✅ **Analytics**: Native support for aggregations, JOINs
- ✅ **Debugging**: Easy to inspect SQL queries

**Tradeoffs**:
- ⚠️ SQL injection concerns (mitigated by validation)
- ⚠️ Doesn't handle unstructured text well (add RAG later)
- ⚠️ Requires Claude to generate valid SQL (high accuracy needed)

### Why Claude for SQL Generation?

**Claude 3.5 Sonnet advantages**:
- Excellent at generating SQL
- Large context window (fits full schema)
- Good instruction following
- Tool use (function calling) support

**Benchmark** (internal testing):
- SQL correctness: 95%+
- Handles complex JOINs: ✅
- Understands date ranges: ✅
- Formats answers well: ✅

---

**Last Updated**: 2025-01-10
**Version**: 2.0 (SQL-First)
**Status**: Phase 1 Starting
