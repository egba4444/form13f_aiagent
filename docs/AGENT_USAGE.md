# Agent Usage Guide

Complete guide for using the Form 13F AI Agent to query institutional holdings data.

## Overview

The Form 13F AI Agent uses Claude (via LiteLLM) to answer natural language questions about SEC Form 13F institutional holdings data. It automatically:

1. Understands your question
2. Generates safe SQL queries
3. Executes queries on PostgreSQL (Supabase)
4. Formats results as natural language

## Setup

### 1. Configure API Key

Get your Anthropic API key from https://console.anthropic.com/

Add to `.env`:
```bash
ANTHROPIC_API_KEY=sk-ant-your-actual-key-here
```

### 2. Verify Configuration

```bash
python scripts/test_agent.py
```

You should see:
```
✅ Agent initialized successfully!
📊 Agent Configuration:
   LLM Provider: anthropic
   LLM Model: claude-3-5-sonnet-20241022
```

## Usage

### Python API

```python
from src.agent import Agent
import os

# Initialize agent
database_url = os.getenv("DATABASE_URL")
agent = Agent(database_url, verbose=True)

# Ask a question
result = agent.query(
    "How many Apple shares did Berkshire Hathaway hold in Q4 2024?",
    include_sql=True
)

if result["success"]:
    print(result["answer"])
    print(f"SQL: {result['sql_query']}")
else:
    print(f"Error: {result['error']}")
```

### Command Line (convenience function)

```python
from src.agent import ask_question

result = ask_question(
    "What are the top 5 managers by portfolio value?",
    include_sql=True
)

print(result["answer"])
```

## Example Questions

### Simple Queries

**Count records:**
```
"How many managers are in the database?"
"How many filings do we have?"
```

**Top N queries:**
```
"What are the top 10 managers by portfolio value?"
"Show me the 5 largest holdings by value"
```

### Manager-Specific

**Single manager:**
```
"How many holdings does Berkshire Hathaway have?"
"What is Vanguard's total portfolio value?"
```

**Manager rankings:**
```
"Where does BlackRock rank by assets?"
"Compare Vanguard and BlackRock portfolio sizes"
```

### Security-Specific

**Holders of a security:**
```
"Who holds Apple stock?"
"Which managers own Tesla?"
```

**Specific positions:**
```
"How many Apple shares did Berkshire Hathaway hold in Q4 2024?"
"What is BlackRock's position in Microsoft?"
```

### Time-Series

**Quarter comparisons:**
```
"Did Berkshire Hathaway increase or decrease their Apple position?"
"Show me Vanguard's portfolio value over time"
```

**Latest data:**
```
"What's the most recent quarter in the database?"
"Show me Q4 2024 filings"
```

### Complex Queries

**Aggregations:**
```
"What's the total value of all Apple holdings across all managers?"
"How many managers hold more than $100 billion in assets?"
```

**Sector analysis (if data loaded):**
```
"Which tech stocks are most popular among hedge funds?"
"What's the total value of Tesla holdings?"
```

## Response Format

The agent returns a dictionary:

```python
{
    "success": True,
    "answer": "Natural language answer...",
    "sql_query": "SELECT ... (if include_sql=True)",
    "raw_data": [...rows...] (if include_raw_data=True),
    "execution_time_ms": 1234,
    "tool_calls": 1,
    "turns": 2
}
```

### Fields

- **success**: bool - Whether query succeeded
- **answer**: str - Natural language answer
- **sql_query**: str (optional) - Generated SQL query
- **all_sql_queries**: list (optional) - All queries if multiple
- **raw_data**: list (optional) - Raw query results
- **execution_time_ms**: int - Total time in milliseconds
- **tool_calls**: int - Number of SQL queries executed
- **turns**: int - Conversation turns taken
- **error**: str (optional) - Error message if failed

## Agent Configuration

### Options

```python
agent = Agent(
    database_url="postgresql://...",
    llm_client=None,  # Custom LLM client (optional)
    verbose=False     # Print debug info
)

result = agent.query(
    question="Your question",
    include_sql=False,      # Include generated SQL
    include_raw_data=False, # Include raw query results
    max_turns=5             # Max conversation turns
)
```

### Verbose Mode

Enable `verbose=True` to see:
- Each conversation turn
- Tool calls being made
- SQL queries generated
- Query results

```python
agent = Agent(database_url, verbose=True)
result = agent.query("How many managers?")
```

Output:
```
🔄 Turn 1/5
🔧 LLM requesting tool use
   Calling: query_database
   Args: {'sql_query': 'SELECT COUNT(*) FROM managers', ...}
   Result: 1 rows
```

## Advanced Usage

### Custom LLM Provider

Switch to OpenAI or another provider:

```python
from src.agent import LLMClient, LLMSettings, Agent

# Configure OpenAI
settings = LLMSettings(
    llm_provider="openai",
    llm_model="gpt-4-turbo-preview",
    openai_api_key="sk-..."
)

llm_client = LLMClient(settings)
agent = Agent(database_url, llm_client=llm_client)
```

### Multi-Turn Conversations

The agent maintains conversation context:

```python
agent = Agent(database_url)

# First question
result1 = agent.query("How many managers are there?")

# Follow-up (context preserved)
result2 = agent.query("What about holdings?")

# Reset context
agent.reset_conversation()
```

### Error Handling

```python
result = agent.query("Your question")

if not result["success"]:
    error = result.get("error")

    if "LLM Error" in error:
        # API issue (rate limit, auth, etc.)
        print("Check your API key and quota")

    elif "SQL Validation Error" in error:
        # Agent generated invalid SQL (shouldn't happen)
        print("SQL validation failed")

    elif "Execution Error" in error:
        # Database error (connection, etc.)
        print("Database issue")
```

## Performance

### Typical Response Times

- Simple queries (count): ~1-2 seconds
- Complex queries (joins): ~2-4 seconds
- Multiple tool calls: ~3-5 seconds

### Factors Affecting Speed

1. **LLM provider**: Claude is typically fast (~1s)
2. **Database**: Supabase vs Docker (Supabase has network latency)
3. **Query complexity**: JOINs and aggregations take longer
4. **Result size**: Large result sets take longer to format

### Optimization Tips

1. **Use compact prompts** for faster token processing
2. **Limit result rows** (already capped at 1000)
3. **Use indexed columns** in WHERE clauses
4. **Switch providers** if one is slow (OpenAI, Gemini, etc.)

## Troubleshooting

### "LLM Error: Missing Anthropic API Key"

**Solution**: Add ANTHROPIC_API_KEY to .env

### "Maximum conversation turns reached"

**Solution**: Increase `max_turns` or reset conversation:
```python
agent.reset_conversation()
```

### "SQL Validation Error: Invalid table"

**Solution**: This shouldn't happen. The agent tried to query a non-existent table. Report as bug.

### Slow responses

**Solution**:
- Check network connection to Supabase
- Try local Docker instead
- Switch LLM provider
- Use compact system prompt

### Wrong answers

**Solution**:
- Verify data is loaded: `SELECT COUNT(*) FROM holdings;`
- Check question phrasing
- Use `include_sql=True` to see generated SQL
- Report incorrect SQL generation as feedback

## Best Practices

### 1. Be Specific

❌ "Tell me about Apple"
✅ "How many Apple shares did Berkshire Hathaway hold in Q4 2024?"

### 2. Use Full Names

❌ "AAPL"
✅ "Apple" or "Apple Inc"

(CUSIP-based queries work too: "CUSIP 037833100")

### 3. Specify Quarters

❌ "Berkshire's holdings"
✅ "Berkshire's holdings in Q4 2024"

### 4. Check Data Availability

Before asking complex questions, verify data is loaded:
```python
ask_question("How many filings are in the database?")
ask_question("What's the most recent quarter?")
```

### 5. Use Verbose Mode for Debugging

```python
agent = Agent(database_url, verbose=True)
```

### 6. Include SQL for Learning

```python
result = agent.query(question, include_sql=True)
print(result["sql_query"])  # Learn SQL patterns
```

## Cost Management

### Token Usage

Each query uses approximately:
- System prompt: ~2,000 tokens
- User question: ~10-50 tokens
- SQL generation: ~100-300 tokens
- Response: ~100-500 tokens

**Total**: ~2,200-2,850 tokens per query

### Cost Estimates (Claude 3.5 Sonnet)

- Input: $3 per 1M tokens
- Output: $15 per 1M tokens

**Per query**: ~$0.01-0.02

### Reducing Costs

1. **Use compact prompts** (`compact=True` in get_system_prompt())
2. **Cache system prompts** (not implemented yet)
3. **Use cheaper models** (Claude Haiku, GPT-3.5)
4. **Switch providers** (Gemini has lower costs)

```python
# Use Claude Haiku (cheaper)
settings = LLMSettings(
    llm_provider="anthropic",
    llm_model="claude-3-haiku-20240307"
)
agent = Agent(database_url, llm_client=LLMClient(settings))
```

## Next Steps

- **Load data**: `python -m src.ingestion.ingest`
- **Build UI**: Phase 6 (Streamlit interface)
- **Deploy API**: Phase 5 (FastAPI backend)
- **Add RAG**: Phase 7 (for commentary/notes)

---

**Last Updated**: 2025-01-12
**Version**: 1.0 (Phase 4)
