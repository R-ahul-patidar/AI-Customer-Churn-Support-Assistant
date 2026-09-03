"""
AI Assistant Orchestrator — Phase 3.

This is the brain of the POST /ask endpoint. It coordinates:
  1. A pre-flight customer lookup (if the question mentions a customer ID)
  2. The LangChain SQL Agent for dynamic data retrieval
  3. A structured Gemini prompt that injects all retrieved context
  4. Response packaging with sources + SQL trace

Flow:
    User question
        │
        ▼
    [Optional] Extract customer_id → fetch customer profile
        │
        ▼
    LangChain SQL Agent
        ├── Introspects DB schema
        ├── Generates + executes SQL
        └── Returns raw data
        │
        ▼
    Gemini (via structured prompt)
        ├── Receives: question + customer profile + SQL results
        └── Returns: natural language answer with reasoning
        │
        ▼
    AskResponse (answer + sql_used + sources)

Phase 4 hook:
    When the ML model is added, predict_churn() will be called here
    and its output injected into the Gemini context before the LLM call.
"""
import logging
import re
from typing import Optional

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from sqlalchemy.orm import Session

from app.config import settings
from app.crud import customer as crud
from app.services.sql_agent import build_sql_agent

logger = logging.getLogger(__name__)

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
4. Keep answers concise but complete. Use bullet points for multi-factor answers.
5. If data is insufficient to answer, say so clearly rather than guessing.
6. When discussing churn rate, express it as a percentage (e.g., 34.5%).
"""

# ---------------------------------------------------------------------------
# Regex to detect a customer ID reference in the question
# e.g. "C102", "customer C-45", "id C1023"
# ---------------------------------------------------------------------------
_CUSTOMER_ID_RE = re.compile(r"\bC[-_]?\d+\b", re.IGNORECASE)


def _extract_customer_id(question: str) -> Optional[str]:
    """
    Scan the question for a customer ID pattern like C102 or C-102.
    Returns the first match normalised to uppercase, or None.
    """
    match = _CUSTOMER_ID_RE.search(question)
    if match:
        # Normalise: remove dashes/underscores, uppercase
        raw = match.group(0).upper().replace("-", "").replace("_", "")
        return raw
    return None


def _format_customer_context(customer) -> str:
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


class AIAssistant:
    """
    Stateless AI assistant — instantiate once per request or as a singleton.

    The assistant is split into two modes:
      - SQL Agent mode: for general questions that need dynamic DB queries
      - Direct Gemini mode: for customer-specific questions where we pre-fetch
        the customer row and inject it as context (faster, more precise)
    """

    def __init__(self):
        self._llm = ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            google_api_key=settings.gemini_api_key,
            temperature=0.2,
        )

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

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

        # Check if question references a specific customer
        customer_id = _extract_customer_id(question)
        customer_context = None
        sources = []

        if customer_id:
            customer = crud.get_customer_by_id(db, customer_id)
            if customer:
                customer_context = _format_customer_context(customer)
                sources.append(f"customer_profile:{customer_id}")
                logger.info("Customer %s found — using direct Gemini mode", customer_id)
                return self._answer_with_customer_context(
                    question=question,
                    customer_context=customer_context,
                    sources=sources,
                    db=db,
                )
            else:
                logger.warning("Customer ID %s mentioned but not found in DB", customer_id)

        # General question — use SQL Agent for dynamic query generation
        return self._answer_with_sql_agent(question=question, sources=sources)

    # ------------------------------------------------------------------
    # Private handlers
    # ------------------------------------------------------------------

    def _answer_with_customer_context(
        self,
        question: str,
        customer_context: str,
        sources: list,
        db: Session,
    ) -> dict:
        """
        For customer-specific questions:
          1. Pre-fetch customer profile (already done by caller)
          2. Also run the SQL agent to get any aggregate context
          3. Combine everything into one Gemini prompt
        """
        # Also fetch aggregate stats to enrich context
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

        # Build the Gemini prompt
        full_context = customer_context + aggregate_context
        human_content = (
            f"Context data:\n{full_context}\n\n"
            f"Question: {question}"
        )

        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=human_content),
        ]

        logger.info("Calling Gemini with customer + aggregate context")
        response = self._llm.invoke(messages)
        if isinstance(response.content, list):
            # When content is structured list of text blocks
            texts = [c.get("text", "") if isinstance(c, dict) else str(c) for c in response.content]
            answer = "".join(texts).strip()
        else:
            answer = str(response.content).strip()

        return {
            "answer": answer,
            "sql_used": sql_used,
            "sources": sources,
        }

    def _answer_with_sql_agent(self, question: str, sources: list) -> dict:
        """
        For general/analytical questions:
          - Builds a fresh SQL agent
          - Lets it introspect the schema and write its own SQL
          - Parses the agent's output back into our response format
        """
        agent = build_sql_agent()
        sources.append("sql_agent:dynamic")

        # Augment the question with role context so the agent's SQL is appropriate
        augmented_question = (
            f"{question}\n\n"
            f"(You are a CRM analyst. Query the customers table. "
            f"Return a clear, data-backed answer with specific numbers.)"
        )

        logger.info("Running SQL agent for general question")
        try:
            result = agent.invoke({"input": augmented_question})
            answer = result.get("output", str(result))
        except Exception as exc:
            logger.exception("SQL agent failed")
            raise RuntimeError(f"SQL agent error: {exc}") from exc

        # Extract the SQL query from the agent's intermediate steps
        sql_used = None
        intermediate = result.get("intermediate_steps", [])
        for step in reversed(intermediate):
            # step is (AgentAction, observation)
            action = step[0]
            action_input = getattr(action, "tool_input", None)
            if isinstance(action_input, dict):
                query = action_input.get("query", "")
                if "SELECT" in query.upper():
                    sql_used = query.strip()
                    break
            elif isinstance(action_input, str) and "SELECT" in action_input.upper():
                sql_used = action_input.strip()
                break

        return {
            "answer": answer,
            "sql_used": sql_used,
            "sources": sources,
        }


# ---------------------------------------------------------------------------
# Module-level singleton — shared across all requests (LLM is thread-safe)
# ---------------------------------------------------------------------------
assistant = AIAssistant()
