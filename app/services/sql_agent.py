"""
SQL Agent — Phase 3.

Wraps the LangChain SQLDatabaseToolkit to give the AI assistant
the ability to:
  1. Introspect the live DB schema (tables + columns) at runtime.
  2. Generate and execute arbitrary SELECT queries on demand.

This means any question the user asks that can be answered from the
customer database is handled dynamically — no hardcoded query needed.
If the schema grows (new columns, new tables), this agent picks it up
automatically without any code changes.

Architecture note:
  - We use langchain_community.utilities.SQLDatabase which wraps
    SQLAlchemy and exposes schema inspection + query execution as
    LangChain tools.
  - The agent is stateless — a fresh agent is constructed per request
    so there is no shared mutable state between HTTP requests.
"""
import logging
from typing import Optional

from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_community.agent_toolkits.sql.base import create_sql_agent
try:
    from langchain.agents import AgentType, AgentExecutor
except ImportError:
    from langchain_classic.agents.agent_types import AgentType
    from langchain_classic.agents.agent import AgentExecutor
from langchain_google_genai import ChatGoogleGenerativeAI

from app.config import settings

logger = logging.getLogger(__name__)


def _get_llm() -> ChatGoogleGenerativeAI:
    """Instantiate the Gemini LLM used by the SQL agent."""
    return ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        google_api_key=settings.gemini_api_key,
        temperature=0.1,       # Low temperature — we want factual SQL, not creative
    )


def build_sql_agent(db_url: Optional[str] = None) -> AgentExecutor:
    """
    Build and return a LangChain SQL agent connected to our SQLite database.

    The agent has access to two tools:
      - sql_db_schema: lists all tables and their column definitions
      - sql_db_query: executes a SELECT statement and returns results

    It uses these tools in a reasoning loop (think → act → observe)
    until it has enough data to answer the user's question.

    Args:
        db_url: Override the database URL (useful for testing). Defaults
                to the configured DATABASE_URL from settings.

    Returns:
        A ready-to-invoke LangChain AgentExecutor.
    """
    url = db_url or settings.database_url
    logger.info("Building SQL agent against database: %s", url)

    # SQLDatabase wraps SQLAlchemy — gives the agent schema-awareness
    db = SQLDatabase.from_uri(
        url,
        include_tables=["customers"],   # Scope to our table only (safe boundary)
        sample_rows_in_table_info=3,    # Show 3 sample rows in schema context
    )

    llm = _get_llm()

    toolkit = SQLDatabaseToolkit(db=db, llm=llm)

    agent_executor = create_sql_agent(
        llm=llm,
        toolkit=toolkit,
        agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True,           # Logs the full reasoning chain — great for debugging
        max_iterations=8,       # Cap the think→act loop to prevent runaway calls
        handle_parsing_errors=True,
        agent_executor_kwargs={"handle_parsing_errors": True, "return_intermediate_steps": True},
    )

    return agent_executor
