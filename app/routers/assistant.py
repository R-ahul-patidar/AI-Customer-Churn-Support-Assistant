"""
AI Assistant router — Phase 3.

Exposes POST /ask — the single endpoint through which users interact
with the AI assistant in natural language.

This router deliberately stays thin:
  - Validates the request (Pydantic)
  - Calls the AIAssistant service
  - Handles errors with clear HTTP responses
  - Returns the structured AskResponse

All AI orchestration logic lives in app/services/ai_assistant.py.
"""
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.assistant import AskRequest, AskResponse
from app.services.ai_assistant import assistant

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/ask",
    tags=["AI Assistant"],
)

DB = Annotated[Session, Depends(get_db)]


@router.post(
    "",
    response_model=AskResponse,
    status_code=status.HTTP_200_OK,
    summary="Ask the AI assistant a question about customer data",
    description="""
Ask any natural-language question about your customer database.

**The assistant can handle two types of questions:**

1. **Customer-specific questions** — mention a customer ID (e.g. `C102`) and the
   assistant pre-fetches that customer's full profile, then uses Gemini to analyse
   and explain their situation.

2. **General / analytical questions** — for anything else, a LangChain SQL Agent
   dynamically inspects the live database schema, writes the appropriate SQL query,
   executes it, and passes the results to Gemini for a natural-language answer.

**Example questions:**
- `"Why is customer C102 at high churn risk?"`
- `"Which plan has the highest churn rate?"`
- `"What is the average monthly spend for churned Premium customers?"`
- `"Show me the 5 customers with the lowest satisfaction scores who haven't churned yet."`
- `"How many customers haven't logged in for more than 45 days?"`

The response always includes `sql_used` (the SQL generated) and `sources` (data
consulted), making it fully auditable.
""",
    responses={
        200: {"description": "AI-generated answer with supporting data"},
        400: {"description": "Invalid or too-short question"},
        503: {"description": "Gemini API key not configured or AI service unavailable"},
    },
)
def ask_assistant(request: AskRequest, db: DB) -> AskResponse:
    """
    Handles POST /ask.

    Routing logic (inside AIAssistant.ask()):
      - If question mentions a customer ID → direct Gemini call with pre-fetched profile
      - Otherwise → LangChain SQL Agent for dynamic query generation
    """
    logger.info("POST /ask  question=%r", request.question[:80])

    # If the caller explicitly provided a customer_id, inject it into the question
    question = request.question
    if request.customer_id and request.customer_id.upper() not in question.upper():
        question = f"[Regarding customer {request.customer_id}] {question}"

    try:
        result = assistant.ask(question=question, db=db)
    except ValueError as exc:
        # Configuration error (missing API key)
        logger.error("Configuration error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        # SQL agent or LLM call failure
        logger.exception("AI assistant runtime error")
        err_msg = str(exc)
        if "ResourceExhausted" in err_msg or "429" in err_msg or "quota" in err_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Gemini API rate limit or free-tier daily quota exceeded. Please switch GEMINI_MODEL in .env to 'gemini-1.5-flash' or 'gemini-2.0-flash', or try again in a moment.",
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"AI assistant error: {exc}",
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected error in AI assistant")
        err_msg = str(exc)
        if "ResourceExhausted" in err_msg or "429" in err_msg or "quota" in err_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Gemini API rate limit or free-tier daily quota exceeded. Please switch GEMINI_MODEL in .env to 'gemini-1.5-flash' or 'gemini-2.0-flash', or try again in a moment.",
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while communicating with the AI service. Please try again.",
        ) from exc

    return AskResponse(
        answer=result["answer"],
        sql_used=result.get("sql_used"),
        sources=result.get("sources", []),
    )
