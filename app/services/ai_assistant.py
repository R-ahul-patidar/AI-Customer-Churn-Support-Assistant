"""
AI Assistant Orchestrator — Phase 3 (Performance Optimized).

Coordinates:
  1. A pre-flight customer lookup (if the question mentions a customer ID or name)
  2. High-speed 2-turn SQL Agent for dynamic data retrieval (~2.8s total)
  3. Structured Gemini prompt for customer-specific context (~2.4s)
  4. In-memory TTL cache for instantaneous responses to frequent / repeated queries (< 0.05s)
  5. Response packaging with sources + SQL trace
"""
import logging
import re
import time
from typing import Any, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from sqlalchemy.orm import Session

from app.config import settings
from app.crud import customer as crud
from app.models.customer import Customer
from app.services.sql_agent import _record_turn, build_sql_agent, get_agent_memory

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-memory TTL query cache
# ---------------------------------------------------------------------------
class QueryCache:
    """Lightweight in-memory LRU cache with TTL expiration for repeated queries."""

    def __init__(self, maxsize: int = 128, ttl_seconds: int = 60):
        self.maxsize = maxsize
        self.ttl_seconds = ttl_seconds
        self._cache: dict[str, tuple[float, dict]] = {}

    def get(self, key: str) -> Optional[dict]:
        if key in self._cache:
            ts, val = self._cache[key]
            if time.time() - ts < self.ttl_seconds:
                return val
            del self._cache[key]
        return None

    def set(self, key: str, val: dict) -> None:
        if len(self._cache) >= self.maxsize:
            oldest = next(iter(self._cache))
            del self._cache[oldest]
        self._cache[key] = (time.time(), val)


_CACHE = QueryCache(maxsize=200, ttl_seconds=60)

# ---------------------------------------------------------------------------
# System prompt — tells Gemini exactly what role to play
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """You are an expert CRM analyst and AI assistant for a customer
churn management platform. You have access to a customer database containing:
  - Customer profiles (age, plan, monthly_spend, tenure_months)
  - Engagement data (support_tickets, last_login_days, satisfaction_score)
  - Churn labels (churn: true/false)

Your job is to answer questions about customer data clearly and actionably.
Rules:
1. Always base your answer on the data provided — do not hallucinate numbers.
2. When identifying churn risk, explain the contributing factors.
3. Recommend specific, concrete actions (e.g., "offer a plan downgrade", "assign a
   dedicated support rep").
4. Keep answers concise, structured, and complete. Use bullet points for multi-factor answers.
5. If data is insufficient to answer, say so clearly rather than guessing.
6. When discussing churn rate, express it as a percentage (e.g., 34.5%).
"""

# ---------------------------------------------------------------------------
# Regex to detect a customer ID reference in the question
# ---------------------------------------------------------------------------
_CUSTOMER_ID_RE = re.compile(r"\bC[-_]?\d+\b", re.IGNORECASE)


def _find_customer(db: Session, question: str) -> Optional[Customer]:
    """
    Search for customer by ID pattern (e.g. C0001, C-0001, C1) or ID mentions.
    Returns the Customer model if found, else None.
    """
    match = _CUSTOMER_ID_RE.search(question)
    if match:
        raw = match.group(0).upper().replace("-", "").replace("_", "")
        customer = crud.get_customer_by_id(db, raw)
        if customer:
            return customer

        # Try zero-padding: e.g. C1 -> C0001
        digits = re.sub(r"\D", "", raw)
        if digits:
            padded = f"C{int(digits):04d}"
            customer = crud.get_customer_by_id(db, padded)
            if customer:
                return customer

    return None


def _format_customer_context(customer: Customer) -> str:
    """Render a customer ORM object as a readable text block."""
    return (
        f"Customer Profile:\n"
        f"  ID: {customer.customer_id}\n"
        f"  Name: {customer.name}\n"
        f"  Age: {customer.age}\n"
        f"  Plan: {customer.plan}\n"
        f"  Monthly Spend: ${customer.monthly_spend:.2f}\n"
        f"  Tenure: {customer.tenure_months} months\n"
        f"  Support Tickets: {customer.support_tickets}\n"
        f"  Last Login: {customer.last_login_days} days ago\n"
        f"  Satisfaction Score: {customer.satisfaction_score}/10\n"
        f"  Churned: {'Yes' if customer.churn else 'No'}\n"
    )


def _extract_text(content: Any) -> str:
    """Safely extracts text regardless of content block type."""
    if isinstance(content, list):
        return "".join(
            [c.get("text", "") if isinstance(c, dict) else str(c) for c in content]
        ).strip()
    return str(content).strip()


class AIAssistant:
    """
    Stateless AI assistant — routes between fast direct customer context
    and high-performance dynamic SQL agent.
    """

    def __init__(self):
        self._llm = ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            google_api_key=settings.gemini_api_key,
            temperature=0.2,
            max_output_tokens=600,
        )

    def ask(self, question: str, db: Session) -> dict:
        """
        Main entry point. Routes the question to the right handler.

        Returns a dict with keys:
          - answer (str)
          - sql_used (str | None)
          - sources (list[str])
        """
        if not settings.gemini_api_key or settings.gemini_api_key == "your_gemini_api_key_here":
            raise ValueError(
                "GEMINI_API_KEY is not configured. "
                "Set it in your .env file (get one free at https://aistudio.google.com/)."
            )

        logger.info("Processing question: %s", question[:120])

        # Check in-memory cache first
        cache_key = question.strip().lower()
        cached_result = _CACHE.get(cache_key)
        if cached_result:
            logger.info("Serving query from TTL cache: %s", cache_key[:50])
            result_copy = dict(cached_result)
            result_copy["sources"] = list(cached_result.get("sources", []))
            if "cache:in_memory" not in result_copy["sources"]:
                result_copy["sources"].append("cache:in_memory")
            return result_copy

        sources: list[str] = []

        # Check if question references a specific customer
        customer = _find_customer(db, question)
        if customer:
            customer_context = _format_customer_context(customer)
            sources.append(f"customer_profile:{customer.customer_id}")
            logger.info("Customer %s found — using direct Gemini mode", customer.customer_id)
            res = self._answer_with_customer_context(
                question=question,
                customer_context=customer_context,
                sources=sources,
                db=db,
            )
            _CACHE.set(cache_key, res)
            return res

        # General analytical question — use high-speed 2-turn SQL Agent
        res = self._answer_with_sql_agent(question=question, sources=sources)
        _CACHE.set(cache_key, res)
        return res

    def _answer_with_customer_context(
        self,
        question: str,
        customer_context: str,
        sources: list[str],
        db: Session,
    ) -> dict:
        """
        For customer-specific questions:
          1. Pre-fetch customer profile
          2. Fetch aggregate stats to enrich context
          3. Fast single-pass Gemini call
        """
        sql_used = None
        aggregate_context = ""
        try:
            stats = crud.get_summary_stats(db)
            aggregate_context = (
                f"\nPlatform-wide context:\n"
                f"  Total customers: {stats['total_customers']}\n"
                f"  Overall churn rate: {stats['churn_rate']}%\n"
                f"  Average monthly spend: ${stats['avg_monthly_spend']:.2f}\n"
                f"  High-risk customers: {stats['high_risk_count']}\n"
            )
            sources.append("analytics:summary")
        except Exception:
            logger.warning("Could not fetch aggregate stats for context enrichment")

        full_context = customer_context + aggregate_context
        human_content = (
            f"Context data:\n{full_context}\n\n"
            f"Question: {question}"
        )

        history = get_agent_memory()
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            *history,
            HumanMessage(content=human_content),
        ]

        logger.info("Calling Gemini with customer + aggregate context")
        response = self._llm.invoke(messages)
        answer = _extract_text(response.content)
        _record_turn(question, answer)

        return {
            "answer": answer,
            "sql_used": sql_used,
            "sources": sources,
        }

    def _answer_with_sql_agent(self, question: str, sources: list[str]) -> dict:
        """
        For general/analytical questions:
          - Uses FastSQLAgent with pre-cached schema
          - Turn 1: Generate SQL (~1.2s)
          - Turn 2: Local SQLite execute (< 2ms) + Synthesize answer (~1.5s)
        """
        agent = build_sql_agent()
        sources.append("sql_agent:dynamic")

        logger.info("Running fast SQL agent for general question")
        try:
            result = agent.invoke({"input": question})
            answer = result.get("output", str(result))
            sql_used = result.get("sql_used")
        except Exception as exc:
            logger.exception("Fast SQL agent failed")
            raise RuntimeError(f"SQL agent error: {exc}") from exc

        return {
            "answer": answer,
            "sql_used": sql_used,
            "sources": sources,
        }


# Singleton instance
assistant = AIAssistant()
