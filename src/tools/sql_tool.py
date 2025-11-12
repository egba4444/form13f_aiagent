"""
SQL Query Tool for LLM Agent

Allows Claude to execute safe SQL queries on the Form 13F database.
Includes validation, execution, and result formatting.
"""

from typing import Dict, List, Any, Optional
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
import time

from .sql_validator import SQLValidator, SQLValidationError
from .schema_loader import SchemaLoader


class SQLQueryTool:
    """
    Tool for executing safe SQL queries.

    Used by LLM agent via function calling to query the database.

    Safety features:
    - Only SELECT queries allowed
    - SQL injection prevention
    - Timeout limits
    - Row limits
    - Table whitelist
    """

    def __init__(
        self,
        database_url: str,
        max_execution_time: int = 5,
        max_rows: int = 1000
    ):
        """
        Initialize SQL query tool.

        Args:
            database_url: PostgreSQL connection string
            max_execution_time: Maximum query execution time in seconds
            max_rows: Maximum number of rows to return
        """
        self.engine = create_engine(database_url)
        self.validator = SQLValidator()
        self.schema_loader = SchemaLoader(database_url)
        self.max_execution_time = max_execution_time
        self.max_rows = max_rows

    def get_tool_definition(self) -> Dict[str, Any]:
        """
        Get tool definition for LLM function calling.

        Returns OpenAI/Anthropic-compatible tool definition.

        Returns:
            Tool definition dict
        """
        # Get schema for tool description
        schema = self.schema_loader.get_compact_schema()

        return {
            "type": "function",
            "function": {
                "name": "query_database",
                "description": f"""Execute SQL query on Form 13F database to retrieve institutional holdings data.

{schema}

Guidelines:
- Use only SELECT statements
- Join tables to get related data (e.g., filings + holdings + issuers)
- Always include LIMIT clause (max {self.max_rows} rows)
- Handle NULL values appropriately
- Use proper date formats (YYYY-MM-DD)
- CIKs are 10 digits with leading zeros
- Values are in USD (not thousands)
""",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "sql_query": {
                            "type": "string",
                            "description": "A valid PostgreSQL SELECT query"
                        },
                        "explanation": {
                            "type": "string",
                            "description": "Brief explanation of what this query retrieves"
                        }
                    },
                    "required": ["sql_query"]
                }
            }
        }

    def execute(
        self,
        sql_query: str,
        explanation: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute SQL query safely.

        Args:
            sql_query: SQL SELECT query
            explanation: Optional explanation of query purpose

        Returns:
            Result dictionary with:
            - success: bool
            - data: List[Dict] (rows as dicts)
            - row_count: int
            - execution_time_ms: int
            - error: Optional[str]
        """
        start_time = time.time()

        try:
            # Validate SQL
            safe_sql = self.validator.validate(sql_query, max_limit=self.max_rows)

            # Execute with timeout
            with self.engine.connect() as conn:
                # Set statement timeout (PostgreSQL-specific)
                conn.execute(text(f"SET statement_timeout = '{self.max_execution_time}s'"))

                # Execute query
                result = conn.execute(text(safe_sql))

                # Fetch rows as dicts
                rows = [dict(row._mapping) for row in result]

            execution_time = int((time.time() - start_time) * 1000)

            return {
                "success": True,
                "data": rows,
                "row_count": len(rows),
                "execution_time_ms": execution_time,
                "sql_executed": safe_sql,
                "explanation": explanation
            }

        except SQLValidationError as e:
            return {
                "success": False,
                "error": f"SQL Validation Error: {str(e)}",
                "data": [],
                "row_count": 0,
                "execution_time_ms": int((time.time() - start_time) * 1000)
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Execution Error: {str(e)}",
                "data": [],
                "row_count": 0,
                "execution_time_ms": int((time.time() - start_time) * 1000)
            }

    def format_results(self, result: Dict[str, Any], max_display: int = 10) -> str:
        """
        Format query results as readable text.

        Args:
            result: Result from execute()
            max_display: Maximum rows to display

        Returns:
            Formatted text
        """
        lines = []

        if not result["success"]:
            lines.append(f"❌ Query failed: {result['error']}")
            return "\n".join(lines)

        lines.append(f"✅ Query succeeded")
        lines.append(f"   Rows returned: {result['row_count']}")
        lines.append(f"   Execution time: {result['execution_time_ms']}ms")

        if result.get("explanation"):
            lines.append(f"   Purpose: {result['explanation']}")

        lines.append("")

        if not result["data"]:
            lines.append("(No results)")
            return "\n".join(lines)

        # Display results as table
        data = result["data"][:max_display]

        if not data:
            lines.append("(No results)")
            return "\n".join(lines)

        # Get column names
        columns = list(data[0].keys())

        # Calculate column widths
        widths = {}
        for col in columns:
            widths[col] = max(
                len(col),
                max(len(str(row.get(col, ''))) for row in data)
            )

        # Header
        header = " | ".join(col.ljust(widths[col]) for col in columns)
        lines.append(header)
        lines.append("-" * len(header))

        # Rows
        for row in data:
            row_str = " | ".join(
                str(row.get(col, '')).ljust(widths[col])
                for col in columns
            )
            lines.append(row_str)

        if result["row_count"] > max_display:
            lines.append(f"... and {result['row_count'] - max_display} more rows")

        return "\n".join(lines)

    def get_schema(self, compact: bool = False) -> str:
        """
        Get database schema.

        Args:
            compact: Return compact version

        Returns:
            Schema text
        """
        if compact:
            return self.schema_loader.get_compact_schema()
        return self.schema_loader.get_schema_text()


# Convenience function for quick use
def query_database(
    sql_query: str,
    database_url: Optional[str] = None,
    explanation: Optional[str] = None
) -> Dict[str, Any]:
    """
    Execute SQL query on database.

    Args:
        sql_query: SQL SELECT query
        database_url: Database URL (or use DATABASE_URL env var)
        explanation: Optional explanation

    Returns:
        Query result dict
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
            "data": [],
            "row_count": 0
        }

    tool = SQLQueryTool(database_url)
    return tool.execute(sql_query, explanation)


# Example usage
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv

    load_dotenv()
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        print("❌ DATABASE_URL not set in .env")
        exit(1)

    tool = SQLQueryTool(database_url)

    print("=" * 60)
    print("SQL Query Tool Test")
    print("=" * 60)

    # Test 1: Get tool definition
    print("\n📋 Tool Definition:")
    tool_def = tool.get_tool_definition()
    print(f"   Function name: {tool_def['function']['name']}")
    print(f"   Parameters: {list(tool_def['function']['parameters']['properties'].keys())}")

    # Test 2: Valid query (with empty database)
    print("\n📊 Test Query (count tables):")
    result = tool.execute(
        "SELECT COUNT(*) as count FROM managers",
        "Count total managers"
    )
    print(tool.format_results(result))

    # Test 3: Invalid query (should fail validation)
    print("\n🚫 Test Invalid Query (should fail):")
    result = tool.execute("DROP TABLE managers")
    print(tool.format_results(result))

    # Test 4: Show schema
    print("\n📄 Database Schema (compact):")
    print(tool.get_schema(compact=True))
