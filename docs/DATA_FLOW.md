# Data Flow Documentation

This document describes how data flows through the Form 13F AI Agent system, from SEC EDGAR to the user's answer.

---

## Table of Contents
- [Ingestion Flow](#ingestion-flow)
- [Query Flow](#query-flow)
- [Data Transformations](#data-transformations)
- [System States](#system-states)

---

## Ingestion Flow

### Overview

```
SEC EDGAR API
    ↓
Raw XML Filing
    ↓
Parse & Extract
    ↓
Enrich with Tickers
    ↓
Textualize Holdings
    ↓
Generate Chunks
    ↓
Create Embeddings
    ↓
Store in Qdrant + Postgres
```

### Detailed Flow

#### Step 1: Download from SEC EDGAR

```python
# Input: CIK, date range
edgar_client.search_filings(cik="0001067983", form_type="13F-HR")

# Output: List of filing metadata
[
    {
        "accession_number": "0001067983-25-000001",
        "cik": "0001067983",
        "filing_date": "2025-02-14",
        "period_of_report": "2024-12-31"
    },
    ...
]
```

**HTTP Request**:
```
GET https://www.sec.gov/cgi-bin/browse-edgar?
    action=getcompany&
    CIK=0001067983&
    type=13F-HR&
    dateb=&
    owner=include&
    count=100
```

**Response**: HTML page with filing links

**Rate Limiting**: Max 10 requests/second

---

#### Step 2: Download Specific Filing

```python
# Input: Accession number
filing = edgar_client.download_filing("0001067983-25-000001")

# Output: FilingDocument object
{
    "xml_content": "<edgarSubmission>...</edgarSubmission>",
    "accession_number": "0001067983-25-000001",
    "filing_url": "https://www.sec.gov/..."
}
```

**File Structure**:
```
Filing Package:
├── Primary document (XML)
├── Information Table (XML)
├── Cover page (HTML/XML)
└── Supporting documents
```

**Storage**: Save to `data/raw/2024/Q4/0001067983-25-000001.xml`

---

#### Step 3: Parse XML

```python
# Input: Raw XML content
parsed = parser.parse(filing.xml_content)

# Output: ParsedFiling object
{
    "metadata": {
        "accession_number": "0001067983-25-000001",
        "cik": "0001067983",
        "manager_name": "Berkshire Hathaway Inc",
        "filing_date": "2025-02-14",
        "period_of_report": "2024-12-31",
        "total_value_thousands": 390500000,
        "number_of_holdings": 45
    },
    "holdings": [
        {
            "cusip": "037833100",
            "issuer_name": "Apple Inc",
            "ticker": None,  # Not in XML, need to enrich
            "value_thousands": 157000000,
            "shares": 916000000,
            "investment_discretion": "SOLE",
            ...
        },
        ...  # 44 more holdings
    ],
    "cover_page_text": "Full text of cover page...",
    "commentary_sections": [
        "Explanatory note 1...",
        "Explanatory note 2..."
    ]
}
```

**XML Parsing**:
- Use lxml for structured data extraction
- XPath queries for specific fields
- Handle multiple schema versions

---

#### Step 4: Enrich with Tickers

```python
# Input: Holdings with CUSIPs
for holding in parsed.holdings:
    holding.ticker = await cusip_resolver.resolve(holding.cusip)

# Output: Holdings with tickers
{
    "cusip": "037833100",
    "issuer_name": "Apple Inc",
    "ticker": "AAPL",  # ← Enriched
    ...
}
```

**CUSIP → Ticker Resolution**:
1. Check local cache
2. Query local database
3. Call OpenFIGI API (if not cached)
4. Store result in database

**OpenFIGI API Call**:
```json
POST https://api.openfigi.com/v3/mapping
{
    "idType": "ID_CUSIP",
    "idValue": "037833100"
}

Response:
{
    "data": [{
        "ticker": "AAPL",
        "name": "APPLE INC",
        "exchCode": "US"
    }]
}
```

---

#### Step 5: Textualize Holdings

```python
# Input: Holding + context
context = PortfolioContext.calculate(parsed.holdings)
text = textualizer.textualize_holding(
    holding=parsed.holdings[0],
    filing=parsed.metadata,
    context=context["037833100"]
)

# Output: Natural language text
"""
Berkshire Hathaway Inc (CIK: 0001067983) held 916,000,000 shares
(916 million) of Apple Inc (AAPL, CUSIP: 037833100) valued at
$157.0 billion as of December 31, 2024.

Position Details:
- Rank by value: 1st (Top 5 holding)
- Portfolio allocation: 40.2%
- Investment discretion: Sole
- Voting authority: Sole on 916,000,000 shares

Change from prior quarter: -4,000,000 shares (-0.4%)
"""
```

**Textualization Process**:
1. Format numbers (916000000 → "916 million")
2. Format currency (157000000000 → "$157.0 billion")
3. Calculate portfolio percentage
4. Determine rank within portfolio
5. Format voting authority
6. Add quarter-over-quarter comparison (if available)
7. Render template

---

#### Step 6: Generate Chunks

```python
# Input: Parsed filing
chunks = chunker.chunk_filing(parsed, prior_quarter=prev_parsed)

# Output: List of TextChunk objects (~60 per filing)
[
    {
        "chunk_type": "holding_detail",
        "text_content": "Berkshire Hathaway held 916M shares of AAPL...",
        "metadata": {
            "accession_number": "0001067983-25-000001",
            "cik": "0001067983",
            "manager_name": "Berkshire Hathaway Inc",
            "ticker": "AAPL",
            "cusip": "037833100",
            "value_thousands": 157000000,
            "position_rank": 1,
            "chunk_type": "holding_detail"
        }
    },
    {
        "chunk_type": "top_holdings",
        "text_content": "Berkshire Hathaway - Top 5 Holdings\n1. AAPL...",
        "metadata": {
            "accession_number": "0001067983-25-000001",
            "cik": "0001067983",
            "chunk_type": "top_holdings",
            "top_n": 5
        }
    },
    ...  # 58 more chunks
]
```

**Chunk Types Generated**:
- 45 holding detail chunks (one per holding)
- 2 summary chunks (top 5, top 10)
- 5 sector summary chunks
- 1 filing overview chunk
- 3 commentary chunks
- 4 comparison chunks (QoQ changes)

**Storage**: Save to `data/processed/0001067983_2024-12-31.json`

---

#### Step 7: Generate Embeddings

```python
# Input: List of text chunks
embeddings = await embedding_generator.generate_for_chunks(chunks)

# Output: List of (chunk, embedding_vector) tuples
[
    (
        chunk1,
        [0.023, -0.15, 0.087, ..., 0.042]  # 1536 dimensions
    ),
    (
        chunk2,
        [-0.11, 0.24, -0.033, ..., 0.19]
    ),
    ...
]
```

**OpenAI API Call**:
```python
POST https://api.openai.com/v1/embeddings
{
    "model": "text-embedding-3-small",
    "input": [
        "Berkshire Hathaway held 916M shares of AAPL...",
        "Berkshire Hathaway held 41.1B in BAC...",
        ...  # Up to 100 texts per request
    ]
}

Response:
{
    "data": [
        {"embedding": [0.023, -0.15, ...]},
        {"embedding": [-0.11, 0.24, ...]},
        ...
    ]
}
```

**Batch Processing**:
- Process 100 chunks per API call
- Rate limit: 3000 RPM
- Add 100ms delay between batches
- Total time: ~1 minute for 100 filings

**Cost**: $0.02 per 1M tokens = $0.03 per 100 filings

---

#### Step 8: Upload to Qdrant

```python
# Input: Chunks with embeddings
points = []
for i, (chunk, embedding) in enumerate(embeddings):
    point = PointStruct(
        id=i,
        vector=embedding,
        payload={
            "text_content": chunk.text_content,
            **chunk.metadata
        }
    )
    points.append(point)

qdrant.upsert(collection_name="form13f_holdings", points=points)

# Output: Points stored in Qdrant
```

**Qdrant Storage**:
```
Collection: form13f_holdings
├── Point 0
│   ├── Vector: [0.023, -0.15, ...]
│   └── Payload: {text: "...", cik: "...", ticker: "AAPL", ...}
├── Point 1
│   ├── Vector: [-0.11, 0.24, ...]
│   └── Payload: {text: "...", cik: "...", ticker: "BAC", ...}
...
```

**Indexes Created**:
- Vector index (HNSW)
- Payload indexes: cik, ticker, manager_name, chunk_type, period_of_report

---

#### Step 9: Store in PostgreSQL (Optional)

```python
# Input: Parsed filing
db.insert_filing(parsed.metadata)
db.bulk_insert_holdings(parsed.holdings)

# Output: Records in PostgreSQL
```

**SQL Tables**:
```sql
filings:
  accession_number | cik        | manager_name           | filing_date | ...
  0001067983-25-01 | 0001067983 | Berkshire Hathaway Inc | 2025-02-14  | ...

holdings:
  id | accession_number | cusip     | ticker | value_thousands | ...
  1  | 0001067983-25-01 | 037833100 | AAPL   | 157000000       | ...
  2  | 0001067983-25-01 | 060505104 | BAC    | 41100000        | ...
  ...
```

---

## Query Flow

### Overview

```
User Question
    ↓
Extract Entities
    ↓
Build Metadata Filter
    ↓
Generate Query Embedding
    ↓
Search Qdrant (similarity + filter)
    ↓
Retrieve Top-K Chunks
    ↓
Format Context for Claude
    ↓
Claude Generates Answer
    ↓
Extract Citations
    ↓
Return to User
```

### Detailed Flow

#### Step 1: User Submits Query

```python
# Input: Natural language question
query = "How many AAPL shares did Berkshire Hathaway hold in Q4 2024?"

# API Request
POST /api/v1/query
{
    "query": "How many AAPL shares did Berkshire Hathaway hold in Q4 2024?",
    "top_k": 10
}
```

---

#### Step 2: Extract Entities

```python
# Input: User query
entities = query_processor.extract_entities(query)

# Output: Extracted entities
{
    "tickers": ["AAPL"],
    "manager_names": ["Berkshire Hathaway"],
    "quarters": [4],
    "years": [2024],
    "cusips": []
}
```

**Entity Extraction Methods**:
- Regex patterns for tickers (2-5 uppercase letters)
- Fuzzy matching against known manager names
- Date parsing (Q4 2024 → date range)
- CUSIP detection (9 alphanumeric characters)

---

#### Step 3: Build Qdrant Filter

```python
# Input: Extracted entities
filter_obj = query_processor.build_qdrant_filter(entities)

# Output: Qdrant filter conditions
{
    "must": [
        {
            "key": "manager_name",
            "match": {"value": "Berkshire Hathaway Inc"}
        },
        {
            "key": "ticker",
            "match": {"value": "AAPL"}
        },
        {
            "key": "period_of_report",
            "range": {
                "gte": "2024-10-01",
                "lte": "2024-12-31"
            }
        }
    ]
}
```

**Date Range Conversion**:
- Q4 2024 → October 1, 2024 to December 31, 2024
- Handles fiscal vs calendar quarters

---

#### Step 4: Generate Query Embedding

```python
# Input: User query
query_vector = await embedding_generator.generate_batch([query])

# Output: 1536-dimensional vector
[0.15, -0.08, 0.23, -0.05, ..., 0.11]
```

**OpenAI API Call** (same as ingestion):
```python
POST https://api.openai.com/v1/embeddings
{
    "model": "text-embedding-3-small",
    "input": ["How many AAPL shares did Berkshire Hathaway hold in Q4 2024?"]
}
```

---

#### Step 5: Search Qdrant

```python
# Input: Query vector + filter
results = qdrant.search(
    collection_name="form13f_holdings",
    query_vector=query_vector,
    query_filter=filter_obj,
    limit=10,
    with_payload=True
)

# Output: Ranked search results
[
    {
        "score": 0.92,  # Similarity score (0-1)
        "payload": {
            "text_content": "Berkshire Hathaway held 916,000,000 shares of AAPL...",
            "accession_number": "0001067983-25-000001",
            "ticker": "AAPL",
            "shares": 916000000,
            ...
        }
    },
    {
        "score": 0.87,
        "payload": {
            "text_content": "Apple Inc position for Berkshire Q4 2024...",
            ...
        }
    },
    ...  # 8 more results
]
```

**Qdrant Search Process**:
1. Apply metadata filter (narrows search space)
2. Compute cosine similarity between query vector and all filtered vectors
3. Return top-K by similarity score
4. Include payload (text + metadata)

**Query Latency**: Typically 30-100ms

---

#### Step 6: Format Context for Claude

```python
# Input: Search results
context = context_builder.format_for_claude(results)

# Output: Formatted context string
"""
Based on the following Form 13F filing information, answer the user's question.

Context from filings:

[Source 1: Berkshire Hathaway Inc, Filing Date: 2025-02-14, Period: 2024-12-31]
Berkshire Hathaway Inc (CIK: 0001067983) held 916,000,000 shares of Apple Inc
(AAPL, CUSIP: 037833100) valued at $157.0 billion as of December 31, 2024.
Position Details: Rank by value: 1st (Top 5 holding)...

[Source 2: ...]
...

Instructions:
- Answer ONLY using the information provided above
- Cite sources by reference number [Source N]
- If the information is not in the context, say "I don't have that information"
- Format numbers clearly

User Question: How many AAPL shares did Berkshire Hathaway hold in Q4 2024?
"""
```

---

#### Step 7: Claude Generates Answer

```python
# Input: Context + system prompt
response = claude.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1000,
    system="You are a financial analyst assistant...",
    messages=[{
        "role": "user",
        "content": context
    }]
)

# Output: Claude's response
{
    "content": [
        {
            "type": "text",
            "text": """According to the Form 13F filing for the period ending
            December 31, 2024, Berkshire Hathaway Inc held 916,000,000 shares
            of Apple Inc (AAPL), valued at $157.0 billion [Source 1].

            This represented their largest holding at 40.2% of the total
            portfolio. The position had sole investment discretion with full
            voting authority on all shares."""
        }
    ]
}
```

**Claude API Latency**: Typically 1-2 seconds

---

#### Step 8: Extract Citations

```python
# Input: Claude's response text
citations = citation_extractor.extract(response.text, results)

# Output: Citations with source metadata
[
    {
        "source_number": 1,
        "accession_number": "0001067983-25-000001",
        "manager_name": "Berkshire Hathaway Inc",
        "filing_date": "2025-02-14",
        "period_of_report": "2024-12-31",
        "chunk_text": "Berkshire Hathaway held 916M shares...",
        "similarity_score": 0.92
    }
]
```

---

#### Step 9: Return to User

```python
# API Response
{
    "answer": "According to the Form 13F filing...",
    "sources": [
        {
            "accession_number": "0001067983-25-000001",
            "manager_name": "Berkshire Hathaway Inc",
            "filing_date": "2025-02-14",
            "similarity_score": 0.92,
            "chunk_text": "..."
        }
    ],
    "query_time_ms": 1850
}
```

**End-to-End Latency Breakdown**:
- Entity extraction: 10ms
- Query embedding: 100ms
- Qdrant search: 50ms
- Context formatting: 10ms
- Claude API: 1500ms
- Response formatting: 30ms
- **Total: ~1.7 seconds**

---

## Data Transformations

### Transformation 1: Raw XML → Structured Holdings

**Input** (XML):
```xml
<infoTable>
  <nameOfIssuer>Apple Inc</nameOfIssuer>
  <cusip>037833100</cusip>
  <value>157000000</value>
  <shrsOrPrnAmt>
    <sshPrnamt>916000000</sshPrnamt>
    <sshPrnamtType>SH</sshPrnamtType>
  </shrsOrPrnAmt>
  <investmentDiscretion>SOLE</investmentDiscretion>
</infoTable>
```

**Output** (Python object):
```python
HoldingRecord(
    cusip="037833100",
    issuer_name="Apple Inc",
    value_thousands=157000000,
    shares_or_principal=916000000,
    sh_or_prn="SH",
    investment_discretion="SOLE"
)
```

### Transformation 2: Structured Holding → Natural Language

**Input** (Python object):
```python
HoldingRecord(
    cusip="037833100",
    issuer_name="Apple Inc",
    ticker="AAPL",
    value_thousands=157000000,
    shares=916000000
)
```

**Output** (Text):
```
Berkshire Hathaway Inc held 916,000,000 shares (916 million) of
Apple Inc (AAPL, CUSIP: 037833100) valued at $157.0 billion...
```

### Transformation 3: Text → Embedding Vector

**Input** (Text):
```
Berkshire Hathaway Inc held 916,000,000 shares of Apple Inc (AAPL)...
```

**Output** (Vector):
```
[0.023, -0.15, 0.087, 0.12, ..., 0.042]  # 1536 dimensions
```

### Transformation 4: Query → Metadata Filter

**Input** (Query):
```
"How many AAPL shares did Berkshire hold in Q4 2024?"
```

**Output** (Filter):
```python
{
    "must": [
        {"key": "manager_name", "match": "Berkshire Hathaway"},
        {"key": "ticker", "match": "AAPL"},
        {"key": "period_of_report", "range": {"gte": "2024-10-01", "lte": "2024-12-31"}}
    ]
}
```

---

## System States

### State Diagram

```
┌─────────────┐
│   Empty     │
│  Database   │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Ingestion  │  ← Download & parse filings
│  In Progress│
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Parsed    │  ← Data in data/processed/
│   Data      │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Embedding  │  ← Generate vectors
│  Generation │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Vectors   │  ← Stored in Qdrant
│  In Qdrant  │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Ready     │  ← System can answer queries
│ for Queries │
└─────────────┘
```

### Data Consistency

**Eventual Consistency Model**:
- Qdrant is source of truth for queries
- PostgreSQL is source of truth for regeneration
- No strong consistency required (filings don't change)

**Sync Strategy**:
- New filings: Ingest → Postgres + Qdrant
- Schema changes: Regenerate from Postgres → Qdrant
- No real-time sync needed (batch processing)

---

**Last Updated**: 2025-01-10
**Version**: 1.0
