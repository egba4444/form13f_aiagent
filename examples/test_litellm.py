"""
Example script to test LiteLLM integration.

This script demonstrates basic LiteLLM usage with the Form 13F AI Agent.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.agent import get_llm_client


def test_basic_completion():
    """Test basic completion"""
    print("=" * 60)
    print("TEST 1: Basic Completion")
    print("=" * 60)

    client = get_llm_client()

    response = client.complete(
        messages=[
            {"role": "user", "content": "What is SEC Form 13F? Please answer in 2-3 sentences."}
        ]
    )

    answer = response.choices[0].message.content
    print(f"\nQuestion: What is SEC Form 13F?")
    print(f"Answer: {answer}\n")


def test_function_calling():
    """Test function calling (tool use)"""
    print("=" * 60)
    print("TEST 2: Function Calling")
    print("=" * 60)

    client = get_llm_client()

    # Define a mock SQL query tool
    tools = [
        {
            "type": "function",
            "function": {
                "name": "query_database",
                "description": "Execute SQL query on Form 13F database to retrieve holdings data",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "sql_query": {
                            "type": "string",
                            "description": "A valid PostgreSQL SELECT query"
                        },
                        "explanation": {
                            "type": "string",
                            "description": "Brief explanation of what the query does"
                        }
                    },
                    "required": ["sql_query"]
                }
            }
        }
    ]

    response = client.complete(
        messages=[
            {
                "role": "system",
                "content": "You have access to a Form 13F database with tables: filings, holdings, managers, issuers."
            },
            {
                "role": "user",
                "content": "Write a SQL query to find the top 10 holdings by value in the most recent quarter."
            }
        ],
        tools=tools,
        tool_choice="auto"
    )

    message = response.choices[0].message

    if message.tool_calls:
        print("\nLLM called a tool!")
        for tool_call in message.tool_calls:
            print(f"  Tool: {tool_call.function.name}")
            print(f"  Arguments: {tool_call.function.arguments}\n")
    else:
        print(f"\nLLM Response: {message.content}\n")


def test_token_counting():
    """Test token counting"""
    print("=" * 60)
    print("TEST 3: Token Counting")
    print("=" * 60)

    client = get_llm_client()

    messages = [
        {"role": "system", "content": "You are a helpful financial analyst assistant."},
        {"role": "user", "content": "How many shares of Apple did Berkshire Hathaway hold?"}
    ]

    token_count = client.count_tokens(messages)
    print(f"\nMessages: {messages}")
    print(f"Token count: {token_count}\n")


def test_configuration():
    """Test configuration display"""
    print("=" * 60)
    print("TEST 4: Current Configuration")
    print("=" * 60)

    client = get_llm_client()

    print(f"\nProvider: {client.settings.llm_provider}")
    print(f"Model: {client.settings.llm_model}")
    print(f"Max Tokens: {client.settings.llm_max_tokens}")
    print(f"Temperature: {client.settings.llm_temperature}")
    print(f"Timeout: {client.settings.llm_timeout}s")
    print(f"LiteLLM Model String: {client.model}\n")


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("LiteLLM Integration Tests")
    print("=" * 60 + "\n")

    try:
        # Test 4: Configuration (doesn't require API key)
        test_configuration()

        # Test 3: Token counting (doesn't require API call)
        test_token_counting()

        # Tests 1 & 2 require valid API key
        print("\nNOTE: The following tests require a valid API key in your .env file\n")

        try:
            test_basic_completion()
            test_function_calling()

            print("=" * 60)
            print("ALL TESTS PASSED! ✅")
            print("=" * 60)

        except Exception as e:
            print(f"\n❌ API tests failed: {e}")
            print("\nThis is expected if you haven't set up your API key yet.")
            print("To fix: Add your API key to .env file:")
            print("  ANTHROPIC_API_KEY=sk-ant-...")

    except Exception as e:
        print(f"\n❌ Configuration test failed: {e}")
        print("\nPlease check your .env file is set up correctly.")


if __name__ == "__main__":
    main()
