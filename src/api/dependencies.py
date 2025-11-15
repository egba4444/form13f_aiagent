"""
FastAPI Dependencies

Provides dependency injection for database sessions, agent, and configuration.
"""

from typing import Generator
from sqlalchemy.orm import Session
from fastapi import Depends
import os

from ..db.session import SessionLocal
from ..agent import Agent, get_llm_client
from ..tools import SQLQueryTool


def get_db() -> Generator[Session, None, None]:
    """
    Database session dependency.

    Yields SQLAlchemy session and ensures cleanup.

    Usage:
        @app.get("/endpoint")
        def endpoint(db: Session = Depends(get_db)):
            # use db session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_database_url() -> str:
    """Get database URL from environment"""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL not configured in environment")
    return database_url


def get_agent() -> Agent:
    """
    Agent dependency.

    Creates and returns AI agent instance.

    Usage:
        @app.post("/query")
        def query(agent: Agent = Depends(get_agent)):
            result = agent.query(question)
    """
    from ..agent.llm_config import LLMClient
    database_url = get_database_url()
    # Create fresh LLM client to avoid singleton caching issues
    llm_client = LLMClient()
    return Agent(database_url, llm_client=llm_client, verbose=False)


def get_sql_tool() -> SQLQueryTool:
    """
    SQL Tool dependency.

    For direct SQL query endpoints (without agent).

    Usage:
        @app.post("/sql")
        def execute_sql(tool: SQLQueryTool = Depends(get_sql_tool)):
            result = tool.execute(sql)
    """
    database_url = get_database_url()
    return SQLQueryTool(database_url)


# Cached instances (optional optimization)
_agent_instance: Agent | None = None
_sql_tool_instance: SQLQueryTool | None = None


def get_cached_agent() -> Agent:
    """
    Get cached agent instance (reuse across requests).

    More efficient but shares state. Use with caution.
    """
    global _agent_instance
    if _agent_instance is None:
        database_url = get_database_url()
        _agent_instance = Agent(database_url, verbose=False)
    return _agent_instance


def get_cached_sql_tool() -> SQLQueryTool:
    """Get cached SQL tool instance"""
    global _sql_tool_instance
    if _sql_tool_instance is None:
        database_url = get_database_url()
        _sql_tool_instance = SQLQueryTool(database_url)
    return _sql_tool_instance
