# LiteLLM Integration Guide

## Overview

This project uses **LiteLLM** to provide a unified interface to 100+ LLM providers. This allows you to easily switch between different LLM providers (Anthropic, OpenAI, Azure, Google, AWS, etc.) without changing your code.

## Why LiteLLM?

**Benefits:**
- ✅ **Provider flexibility**: Switch between 100+ LLM providers with just config changes
- ✅ **Unified API**: Consistent OpenAI-compatible interface for all providers
- ✅ **Cost optimization**: Compare costs and switch to cheaper providers
- ✅ **Fallback support**: Automatic fallback to backup providers if primary fails
- ✅ **Function calling**: Unified tool/function calling across providers
- ✅ **Streaming**: Consistent streaming API
- ✅ **Token counting**: Accurate token counting for any provider
- ✅ **Async support**: Native async/await support

**Supported Providers:**
- Anthropic (Claude)
- OpenAI (GPT-4, GPT-3.5)
- Azure OpenAI
- Google (Gemini, PaLM)
- AWS Bedrock (Claude, Titan, Jurassic)
- Cohere
- Replicate
- Hugging Face
- Together AI
- Anyscale
- And 90+ more...

## Configuration

### Environment Variables

Set these in your `.env` file:

```bash
# Provider Selection
LLM_PROVIDER="anthropic"              # Provider name
LLM_MODEL="claude-3-5-sonnet-20241022" # Model identifier

# API Keys (set the one for your provider)
ANTHROPIC_API_KEY="sk-ant-..."
OPENAI_API_KEY="sk-..."
AZURE_API_KEY="..."
GEMINI_API_KEY="..."

# Optional Configuration
LLM_BASE_URL=""          # Custom base URL (for proxies/self-hosted)
LLM_MAX_TOKENS="4096"    # Max tokens per completion
LLM_TEMPERATURE="0.0"    # Temperature (0.0 = deterministic)
LLM_TIMEOUT="60"         # Request timeout in seconds
LITELLM_LOG_LEVEL="ERROR" # Log level: DEBUG, INFO, WARNING, ERROR
```

### Provider Examples

#### Anthropic Claude (Default)
```bash
LLM_PROVIDER="anthropic"
LLM_MODEL="claude-3-5-sonnet-20241022"
ANTHROPIC_API_KEY="sk-ant-..."
```

Models:
- `claude-3-5-sonnet-20241022` (latest, best for coding)
- `claude-3-opus-20240229` (most capable)
- `claude-3-sonnet-20240229` (balanced)
- `claude-3-haiku-20240307` (fastest, cheapest)

#### OpenAI GPT
```bash
LLM_PROVIDER="openai"
LLM_MODEL="gpt-4-turbo-preview"
OPENAI_API_KEY="sk-..."
```

Models:
- `gpt-4-turbo-preview` (latest GPT-4)
- `gpt-4` (stable)
- `gpt-3.5-turbo` (fast, cheap)

#### Azure OpenAI
```bash
LLM_PROVIDER="azure"
LLM_MODEL="gpt-4"
AZURE_API_KEY="..."
LLM_BASE_URL="https://your-resource.openai.azure.com/"
```

#### Google Gemini
```bash
LLM_PROVIDER="gemini"
LLM_MODEL="gemini-pro"
GEMINI_API_KEY="..."
```

Models:
- `gemini-pro` (text)
- `gemini-pro-vision` (multimodal)

#### AWS Bedrock Claude
```bash
LLM_PROVIDER="bedrock"
LLM_MODEL="anthropic.claude-3-sonnet-20240229-v1:0"
AWS_ACCESS_KEY_ID="..."
AWS_SECRET_ACCESS_KEY="..."
AWS_REGION_NAME="us-east-1"
```

## Usage Examples

### Basic Completion

```python
from src.agent import get_llm_client

# Get client (reads from environment)
client = get_llm_client()

# Simple completion
response = client.complete(
    messages=[
        {"role": "user", "content": "What is the capital of France?"}
    ]
)

print(response.choices[0].message.content)
# Output: "The capital of France is Paris."
```

### Function Calling (Tool Use)

```python
from src.agent import get_llm_client

client = get_llm_client()

# Define tools
tools = [
    {
        "type": "function",
        "function": {
            "name": "query_database",
            "description": "Execute SQL query on Form 13F database",
            "parameters": {
                "type": "object",
                "properties": {
                    "sql_query": {
                        "type": "string",
                        "description": "PostgreSQL SELECT query"
                    }
                },
                "required": ["sql_query"]
            }
        }
    }
]

# Call with tools
response = client.complete(
    messages=[
        {"role": "user", "content": "How many AAPL shares did Berkshire hold?"}
    ],
    tools=tools,
    tool_choice="auto"
)

# Check if tool was called
message = response.choices[0].message
if message.tool_calls:
    for tool_call in message.tool_calls:
        print(f"Tool: {tool_call.function.name}")
        print(f"Args: {tool_call.function.arguments}")
```

### Streaming Responses

```python
from src.agent import get_llm_client

client = get_llm_client()

# Stream completion
stream = client.complete(
    messages=[
        {"role": "user", "content": "Write a SQL query to find top holdings"}
    ],
    stream=True
)

# Process stream
for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="", flush=True)
```

### Async Usage

```python
from src.agent import get_llm_client
import asyncio

async def query_llm():
    client = get_llm_client()

    response = await client.acomplete(
        messages=[
            {"role": "user", "content": "Hello!"}
        ]
    )

    return response.choices[0].message.content

# Run async
result = asyncio.run(query_llm())
print(result)
```

### Token Counting

```python
from src.agent import get_llm_client

client = get_llm_client()

messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "What is Form 13F?"}
]

# Count tokens
token_count = client.count_tokens(messages)
print(f"Tokens: {token_count}")
```

### Custom Settings

```python
from src.agent import LLMClient, LLMSettings

# Create custom settings
settings = LLMSettings(
    llm_provider="openai",
    llm_model="gpt-4",
    openai_api_key="sk-...",
    llm_max_tokens=8000,
    llm_temperature=0.7
)

# Create client with custom settings
client = LLMClient(settings)

response = client.complete(
    messages=[{"role": "user", "content": "Hello"}]
)
```

## Cost Comparison

Use LiteLLM to compare costs across providers:

| Provider | Model | Cost per 1M tokens (input/output) |
|----------|-------|-----------------------------------|
| Anthropic | Claude 3.5 Sonnet | $3 / $15 |
| Anthropic | Claude 3 Haiku | $0.25 / $1.25 |
| OpenAI | GPT-4 Turbo | $10 / $30 |
| OpenAI | GPT-3.5 Turbo | $0.50 / $1.50 |
| Google | Gemini Pro | $0.50 / $1.50 |

**Cost optimization tip**: Use cheaper models (Haiku, GPT-3.5) for simple queries, reserve expensive models (Sonnet, GPT-4) for complex reasoning.

## Switching Providers

To switch providers, just update your `.env` file:

### Example: Switch from Anthropic to OpenAI

**Before (Anthropic):**
```bash
LLM_PROVIDER="anthropic"
LLM_MODEL="claude-3-5-sonnet-20241022"
ANTHROPIC_API_KEY="sk-ant-..."
```

**After (OpenAI):**
```bash
LLM_PROVIDER="openai"
LLM_MODEL="gpt-4-turbo-preview"
OPENAI_API_KEY="sk-..."
```

**No code changes needed!** Your application will automatically use the new provider.

## Fallback Configuration

Configure automatic fallback to backup providers if primary fails:

```python
from litellm import completion

# LiteLLM supports fallback natively
response = completion(
    model="claude-3-5-sonnet-20241022",
    messages=[{"role": "user", "content": "Hello"}],
    fallbacks=["gpt-4", "gpt-3.5-turbo"]  # Try these if Claude fails
)
```

## Troubleshooting

### Authentication Errors

**Problem**: `AuthenticationError: Invalid API key`

**Solution**:
1. Check you've set the correct API key for your provider
2. Ensure the key is active and has credits
3. Verify you're using the right environment variable:
   - Anthropic: `ANTHROPIC_API_KEY`
   - OpenAI: `OPENAI_API_KEY`
   - Azure: `AZURE_API_KEY`

### Rate Limits

**Problem**: `RateLimitError: Rate limit exceeded`

**Solution**:
1. Add retry logic with exponential backoff
2. Switch to a provider with higher limits
3. Use LiteLLM's built-in rate limit handling

### Model Not Found

**Problem**: `NotFoundError: Model not found`

**Solution**:
1. Check model name is correct for your provider
2. Verify you have access to the model (some require waitlist)
3. See LiteLLM docs for correct model names: https://docs.litellm.ai/docs/providers

### Timeout Errors

**Problem**: Requests timing out

**Solution**:
1. Increase `LLM_TIMEOUT` in `.env`
2. Reduce `LLM_MAX_TOKENS` for faster responses
3. Use a faster model (e.g., Claude Haiku instead of Opus)

## Advanced Features

### Custom Base URLs (Proxies)

Use LiteLLM with proxy servers or self-hosted endpoints:

```bash
# Example: Using a proxy
LLM_BASE_URL="https://your-proxy.com/v1"
```

### Caching

Enable LiteLLM's caching to save costs on repeated queries:

```python
import litellm
litellm.cache = litellm.Cache()

# Cached completion
response = client.complete(
    messages=[{"role": "user", "content": "What is Form 13F?"}],
    caching=True
)
```

### Logging

Enable detailed logging for debugging:

```bash
LITELLM_LOG_LEVEL="DEBUG"
```

Or in code:
```python
import litellm
litellm.set_verbose = True
```

## Production Recommendations

For production deployments:

1. **Use environment-specific settings**:
   - Development: Use cheaper models (Haiku, GPT-3.5)
   - Production: Use best models (Sonnet, GPT-4)

2. **Set timeouts**: Always set `LLM_TIMEOUT` to prevent hanging requests

3. **Monitor costs**: Use LiteLLM's cost tracking:
   ```python
   response = client.complete(messages=...)
   print(f"Cost: ${response._hidden_params.get('response_cost', 0)}")
   ```

4. **Configure fallbacks**: Have backup providers for reliability

5. **Cache aggressively**: Enable caching for repeated queries

6. **Log everything**: Keep logs for debugging and auditing

## Resources

- **LiteLLM Docs**: https://docs.litellm.ai/
- **Supported Providers**: https://docs.litellm.ai/docs/providers
- **Function Calling**: https://docs.litellm.ai/docs/completion/function_call
- **Cost Tracking**: https://docs.litellm.ai/docs/completion/cost_tracking
- **GitHub**: https://github.com/BerriAI/litellm

## Migration from Anthropic SDK

If you previously used the Anthropic SDK directly, here's the migration:

### Before (Anthropic SDK)
```python
from anthropic import Anthropic

client = Anthropic(api_key="sk-ant-...")
response = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=4096,
    messages=[{"role": "user", "content": "Hello"}]
)
print(response.content[0].text)
```

### After (LiteLLM)
```python
from src.agent import get_llm_client

client = get_llm_client()
response = client.complete(
    messages=[{"role": "user", "content": "Hello"}]
)
print(response.choices[0].message.content)
```

**Key differences:**
- LiteLLM uses OpenAI-style response format (`.choices[0].message.content`)
- Configuration is in environment variables, not code
- Can switch providers without code changes

---

**Last Updated**: 2025-01-12
**LiteLLM Version**: 1.53.0+
