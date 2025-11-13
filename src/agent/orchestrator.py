"""
Agent Orchestrator for Form 13F AI Agent.

Coordinates between LLM (via LiteLLM) and SQL Query Tool to answer
natural language questions about Form 13F institutional holdings.
"""

from typing import List, Dict, Any, Optional
import json
import time

from .llm_config import LLMClient, get_llm_client
from .prompts import get_system_prompt
from ..tools.sql_tool import SQLQueryTool
from ..tools.schema_loader import SchemaLoader


class Agent:
    """
    Form 13F AI Agent.

    Orchestrates LLM and SQL Tool to answer questions about institutional holdings.

    Flow:
    1. User asks question
    2. Agent provides system prompt + database schema
    3. LLM generates SQL via tool use
    4. Agent executes SQL safely
    5. Agent returns results to LLM
    6. LLM formats natural language answer
    """

    def __init__(
        self,
        database_url: str,
        llm_client: Optional[LLMClient] = None,
        verbose: bool = False
    ):
        """
        Initialize agent.

        Args:
            database_url: PostgreSQL connection string
            llm_client: LLM client (defaults to get_llm_client())
            verbose: Print debug information
        """
        self.database_url = database_url
        self.llm_client = llm_client or get_llm_client()
        self.sql_tool = SQLQueryTool(database_url)
        self.schema_loader = SchemaLoader(database_url)
        self.verbose = verbose

        # Conversation history (for multi-turn conversations)
        self.conversation_history: List[Dict[str, str]] = []

        # Get system prompt with schema
        schema = self.schema_loader.get_schema_text(include_samples=True)
        self.system_prompt = get_system_prompt(schema, compact=False)

    def query(
        self,
        question: str,
        include_sql: bool = False,
        include_raw_data: bool = False,
        max_turns: int = 5
    ) -> Dict[str, Any]:
        """
        Answer a question about Form 13F data.

        Args:
            question: User's natural language question
            include_sql: Include generated SQL in response
            include_raw_data: Include raw query results in response
            max_turns: Maximum conversation turns (prevent infinite loops)

        Returns:
            Response dict with:
            - answer: Natural language answer
            - sql_query: Optional[str] (if include_sql=True)
            - raw_data: Optional[List[Dict]] (if include_raw_data=True)
            - execution_time_ms: int
            - tool_calls: List of tool calls made
        """
        start_time = time.time()

        # Add user message to conversation
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": question}
        ]

        # Get SQL tool definition
        tool_def = self.sql_tool.get_tool_definition()

        sql_queries = []
        raw_data = None
        tool_calls_made = []

        # Conversation loop (handle tool calls)
        for turn in range(max_turns):
            if self.verbose:
                print(f"\n🔄 Turn {turn + 1}/{max_turns}")

            # Call LLM
            try:
                response = self.llm_client.complete(
                    messages=messages,
                    tools=[tool_def],
                    tool_choice="auto"
                )
            except Exception as e:
                return {
                    "success": False,
                    "error": f"LLM Error: {str(e)}",
                    "answer": f"I encountered an error while processing your question: {str(e)}",
                    "execution_time_ms": int((time.time() - start_time) * 1000),
                    "tool_calls": len(tool_calls_made),
                    "turns": turn + 1
                }

            assistant_message = response.choices[0].message

            # Check if LLM wants to use a tool
            if hasattr(assistant_message, 'tool_calls') and assistant_message.tool_calls:
                if self.verbose:
                    print(f"🔧 LLM requesting tool use")

                # Add assistant message to conversation
                messages.append({
                    "role": "assistant",
                    "content": assistant_message.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        }
                        for tc in assistant_message.tool_calls
                    ]
                })

                # Execute each tool call
                for tool_call in assistant_message.tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)

                    if self.verbose:
                        print(f"   Calling: {function_name}")
                        print(f"   Args: {function_args}")

                    # Execute SQL query
                    if function_name == "query_database":
                        sql_query = function_args.get("sql_query")
                        explanation = function_args.get("explanation")

                        result = self.sql_tool.execute(sql_query, explanation)

                        if self.verbose:
                            print(f"   Result: {result.get('row_count', 0)} rows")

                        # Save for response
                        sql_queries.append(sql_query)
                        if include_raw_data and result.get("success"):
                            raw_data = result.get("data", [])

                        # Record tool call
                        tool_calls_made.append({
                            "function": function_name,
                            "arguments": function_args,
                            "result": result
                        })

                        # Add tool result to conversation
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": function_name,
                            "content": json.dumps(result)
                        })

                # Continue conversation with tool results
                continue

            else:
                # LLM provided final answer
                answer = assistant_message.content

                execution_time = int((time.time() - start_time) * 1000)

                response_dict = {
                    "success": True,
                    "answer": answer,
                    "execution_time_ms": execution_time,
                    "tool_calls": len(tool_calls_made),
                    "turns": turn + 1
                }

                if include_sql and sql_queries:
                    response_dict["sql_query"] = sql_queries[-1]  # Latest query
                    response_dict["all_sql_queries"] = sql_queries

                if include_raw_data and raw_data is not None:
                    response_dict["raw_data"] = raw_data

                return response_dict

        # Max turns reached
        return {
            "success": False,
            "error": f"Maximum conversation turns ({max_turns}) reached",
            "answer": "I apologize, but I wasn't able to complete your request within the allowed number of steps.",
            "execution_time_ms": int((time.time() - start_time) * 1000),
            "tool_calls": len(tool_calls_made)
        }

    def reset_conversation(self):
        """Clear conversation history"""
        self.conversation_history = []


# Convenience function
def ask_question(
    question: str,
    database_url: Optional[str] = None,
    include_sql: bool = False,
    verbose: bool = False
) -> Dict[str, Any]:
    """
    Ask a question about Form 13F data.

    Args:
        question: Natural language question
        database_url: Database URL (or use DATABASE_URL env var)
        include_sql: Include generated SQL in response
        verbose: Print debug information

    Returns:
        Response dict with answer
    """
    if database_url is None:
        import os
        from dotenv import load_dotenv
        load_dotenv()
        database_url = os.getenv("DATABASE_URL")

    if not database_url:
        return {
            "success": False,
            "error": "DATABASE_URL not configured",
            "answer": "Database connection not configured."
        }

    agent = Agent(database_url, verbose=verbose)
    return agent.query(question, include_sql=include_sql)


# Example usage
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv

    load_dotenv()
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        print("❌ DATABASE_URL not set in .env")
        exit(1)

    # Note: This requires ANTHROPIC_API_KEY to be set
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("❌ ANTHROPIC_API_KEY not set in .env")
        print("   Add your API key to .env to test the agent")
        exit(1)

    agent = Agent(database_url, verbose=True)

    print("=" * 60)
    print("Form 13F AI Agent - Interactive Demo")
    print("=" * 60)

    # Example question
    question = "How many managers are in the database?"

    print(f"\n❓ Question: {question}\n")

    result = agent.query(question, include_sql=True)

    if result["success"]:
        print(f"✅ Answer: {result['answer']}\n")

        if result.get("sql_query"):
            print(f"📝 SQL Generated:\n{result['sql_query']}\n")

        print(f"⏱️  Execution time: {result['execution_time_ms']}ms")
        print(f"🔧 Tool calls: {result['tool_calls']}")
        print(f"🔄 Turns: {result['turns']}")
    else:
        print(f"❌ Error: {result.get('error')}")
