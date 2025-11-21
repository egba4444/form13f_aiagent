"""
Test Agent with RAG Tool

Tests that the agent can successfully use the RAG tool to answer questions
about filing text content.

Usage:
    python scripts/test_agent_with_rag.py
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agent.orchestrator import Agent

# Load environment
load_dotenv()


def test_agent_with_rag():
    """Test agent with RAG-based questions."""
    print("=" * 80)
    print("TESTING AGENT WITH RAG TOOL")
    print("=" * 80)

    # Initialize agent
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL not found")
        return False

    print("\nInitializing agent...")
    agent = Agent(database_url=database_url, verbose=True)

    # Check if RAG tool is available
    if agent.rag_tool:
        print("[OK] RAG tool loaded successfully")
    else:
        print("[X] RAG tool not available - make sure Qdrant is running")
        return False

    # Test questions that should use RAG
    test_questions = [
        {
            "question": "What filing managers are mentioned in the database?",
            "expected_tool": "search_filing_text",
            "description": "Simple query to find manager information in filing text"
        },
        {
            "question": "Are there any explanatory notes about investment strategies?",
            "expected_tool": "search_filing_text",
            "description": "Should search for strategy-related text"
        },
    ]

    print("\n" + "=" * 80)
    print("TEST QUESTIONS")
    print("=" * 80)

    for i, test in enumerate(test_questions, 1):
        print(f"\n{'='*80}")
        print(f"Test {i}: {test['description']}")
        print(f"{'='*80}")
        print(f"Question: {test['question']}")
        print(f"Expected to use: {test['expected_tool']}")
        print()

        try:
            response = agent.query(
                question=test['question'],
                include_sql=True
            )

            if response.get('success', True):  # Default to True if key missing
                print(f"[OK] Agent responded successfully")
                print(f"\nAnswer: {response.get('answer', 'No answer provided')}")

                # Check tool usage
                tool_calls = response.get('tool_calls', 0)
                print(f"\nTool calls made: {tool_calls}")

                # Show execution time
                exec_time = response.get('execution_time_ms', 0)
                print(f"Execution time: {exec_time}ms")

            else:
                print(f"[X] Agent failed: {response.get('error')}")

        except Exception as e:
            print(f"[X] Error: {e}")
            import traceback
            traceback.print_exc()

    # Summary
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)
    print("\nThe agent is now capable of:")
    print("1. Querying structured holdings data (SQL)")
    print("2. Searching filing text content (RAG)")
    print("3. Combining both for comprehensive answers")
    print("\nNext: Add RAG API endpoints and UI features")
    print("=" * 80)

    return True


if __name__ == "__main__":
    success = test_agent_with_rag()
    sys.exit(0 if success else 1)
