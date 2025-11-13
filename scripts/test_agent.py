"""Test Form 13F AI Agent"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.agent import Agent
from dotenv import load_dotenv
import os

# Fix Unicode encoding for Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def main():
    load_dotenv()
    database_url = os.getenv("DATABASE_URL")
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")

    print("=" * 60)
    print("Form 13F AI Agent Test")
    print("=" * 60)

    # Check configuration
    print("\n📋 Configuration Check:")
    print(f"   Database: {'✅ Connected' if database_url else '❌ Not configured'}")
    print(f"   API Key: {'✅ Set' if anthropic_api_key and anthropic_api_key != 'sk-ant-your-key-here' else '❌ Not set'}")

    if not database_url:
        print("\n❌ DATABASE_URL not set in .env")
        return 1

    if not anthropic_api_key or anthropic_api_key == "sk-ant-your-key-here":
        print("\n⚠️  ANTHROPIC_API_KEY not set in .env")
        print("\nTo test the agent with Claude:")
        print("1. Get API key from: https://console.anthropic.com/")
        print("2. Add to .env: ANTHROPIC_API_KEY=sk-ant-your-actual-key")
        print("\n📝 Showing agent setup (without making API calls)...\n")

        # Show what the agent would do
        agent = Agent(database_url, verbose=False)

        print("✅ Agent initialized successfully!")
        print(f"\n📊 Agent Configuration:")
        print(f"   LLM Provider: {agent.llm_client.settings.llm_provider}")
        print(f"   LLM Model: {agent.llm_client.settings.llm_model}")
        print(f"   Max Tokens: {agent.llm_client.settings.llm_max_tokens}")
        print(f"   Temperature: {agent.llm_client.settings.llm_temperature}")

        print(f"\n🔧 Tools Available:")
        tool_def = agent.sql_tool.get_tool_definition()
        print(f"   - {tool_def['function']['name']}")

        print(f"\n📄 System Prompt Length: {len(agent.system_prompt)} characters")

        print("\n📝 Example Questions (once API key is set):")
        example_questions = [
            "How many managers are in the database?",
            "What are the top 5 managers by portfolio value?",
            "How many Apple shares did Berkshire Hathaway hold?",
            "Who holds the most Tesla stock?",
        ]
        for i, q in enumerate(example_questions, 1):
            print(f"   {i}. {q}")

        return 0

    # API key is set, run actual test
    print("\n🚀 Testing Agent with Claude...\n")

    agent = Agent(database_url, verbose=True)

    # Test question (simple query to start)
    question = "How many managers are in the database?"

    print(f"❓ Question: {question}\n")

    try:
        result = agent.query(question, include_sql=True)

        if result.get("success"):
            print("\n" + "=" * 60)
            print("✅ SUCCESS!")
            print("=" * 60)
            print(f"\n📝 Answer:\n{result['answer']}\n")

            if result.get("sql_query"):
                print(f"🔍 SQL Generated:")
                print(f"{result['sql_query']}\n")

            print(f"⏱️  Execution time: {result['execution_time_ms']}ms")
            print(f"🔧 Tool calls made: {result['tool_calls']}")
            print(f"🔄 Conversation turns: {result['turns']}")

        else:
            print("\n" + "=" * 60)
            print("❌ FAILED")
            print("=" * 60)
            print(f"\nError: {result.get('error')}")
            print(f"Answer: {result.get('answer')}")

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        print("\nThis might be due to:")
        print("  - Invalid API key")
        print("  - Network issues")
        print("  - Rate limiting")
        return 1

    print("\n" + "=" * 60)
    print("Test complete!")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    exit(main())
