"""
Analytics router — Phase 2.
Exposes all SQL analytics queries built in Phase 1 CRUD layer as REST endpoints.

All queries use SQLAlchemy (ORM or Core) — raw SQL is visible in crud/customer.py
for demonstration purposes. No business logic lives here; routers stay thin.
"""
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.crud import customer as crud
from app.database import get_db
from app.schemas.analytics import (
    AvgSpendByPlanResponse,
    ChurnByPlanResponse,
    HighRiskResponse,
    HighTicketResponse,
    SummaryStats,
    TopSpendersResponse,
)
from app.schemas.customer import CustomerResponse

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"],
)

# Shared DB dependency alias for cleaner signatures
DB = Annotated[Session, Depends(get_db)]


# ---------------------------------------------------------------------------
# GET /analytics (Consolidated Overview — Assessment Table)
# ---------------------------------------------------------------------------

@router.get(
    "",
    summary="Consolidated Customer & Churn Analytics",
    description="Returns a consolidated analytics payload matching Assessment endpoint: GET /analytics.",
)
def get_analytics(db: DB):
    """Aggregated customer and churn analytics overview."""
    logger.info("GET /analytics")
    try:
        return {
            "summary": crud.get_summary_stats(db),
            "churn_by_plan": crud.get_churn_rate_by_plan(db),
            "avg_spend_by_plan": crud.get_avg_spend_by_plan(db),
            "top_spenders": [CustomerResponse.model_validate(c) for c in crud.get_top_spenders(db, limit=5)],
        }
    except Exception as exc:
        logger.exception("Error computing consolidated analytics")
        raise HTTPException(status_code=500, detail="Failed to fetch analytics") from exc


# ---------------------------------------------------------------------------
# GET /analytics/summary
# ---------------------------------------------------------------------------

@router.get(
    "/summary",
    response_model=SummaryStats,
    summary="Dashboard summary statistics",
    description=(
        "Returns a single-object snapshot of the most important KPIs: "
        "total customers, churn counts, overall churn rate, average monthly "
        "spend, and the number of customers currently flagged as high-risk."
    ),
)
def analytics_summary(db: DB):
    """Aggregate dashboard figures — one DB round-trip per scalar."""
    logger.info("GET /analytics/summary")
    try:
        stats = crud.get_summary_stats(db)
    except Exception as exc:
        logger.exception("Error computing summary stats")
        raise HTTPException(status_code=500, detail="Failed to compute summary statistics") from exc
    return stats


# ---------------------------------------------------------------------------
# GET /analytics/top-spenders
# ---------------------------------------------------------------------------

@router.get(
    "/top-spenders",
    response_model=TopSpendersResponse,
    summary="Top N customers by monthly spend",
    description=(
        "Returns the top `limit` customers ordered by monthly_spend descending. "
        "Useful for identifying high-value accounts at risk of churning."
    ),
)
def analytics_top_spenders(
    db: DB,
    limit: int = Query(10, ge=1, le=100, description="How many top spenders to return (max 100)"),
):
    """Fetch top-N spenders from the database."""
    logger.info("GET /analytics/top-spenders  limit=%d", limit)
    try:
        customers = crud.get_top_spenders(db, limit=limit)
    except Exception as exc:
        logger.exception("Error fetching top spenders")
        raise HTTPException(status_code=500, detail="Failed to fetch top spenders") from exc

    return TopSpendersResponse(
        limit=limit,
        results=[CustomerResponse.model_validate(c) for c in customers],
    )


# ---------------------------------------------------------------------------
# GET /analytics/churn-by-plan
# ---------------------------------------------------------------------------

@router.get(
    "/churn-by-plan",
    response_model=ChurnByPlanResponse,
    summary="Churn rate grouped by subscription plan",
    description=(
        "Aggregates churned vs. total customers for each plan (Basic, Standard, "
        "Premium) and returns a churn_rate percentage per plan, sorted by "
        "churn_rate descending."
    ),
)
def analytics_churn_by_plan(db: DB):
    """Return churn statistics broken down by subscription plan."""
    logger.info("GET /analytics/churn-by-plan")
    try:
        rows = crud.get_churn_rate_by_plan(db)
    except Exception as exc:
        logger.exception("Error computing churn by plan")
        raise HTTPException(status_code=500, detail="Failed to compute churn by plan") from exc
    return ChurnByPlanResponse(results=rows)


# ---------------------------------------------------------------------------
# GET /analytics/avg-spend-by-plan
# ---------------------------------------------------------------------------

@router.get(
    "/avg-spend-by-plan",
    response_model=AvgSpendByPlanResponse,
    summary="Average monthly spend per subscription plan",
    description=(
        "Shows the mean monthly_spend and customer count for each plan, "
        "ordered by average spend descending."
    ),
)
def analytics_avg_spend_by_plan(db: DB):
    """Return average spend statistics grouped by plan."""
    logger.info("GET /analytics/avg-spend-by-plan")
    try:
        rows = crud.get_avg_spend_by_plan(db)
    except Exception as exc:
        logger.exception("Error computing avg spend by plan")
        raise HTTPException(status_code=500, detail="Failed to compute average spend by plan") from exc
    return AvgSpendByPlanResponse(results=rows)


# ---------------------------------------------------------------------------
# GET /analytics/high-ticket-customers
# ---------------------------------------------------------------------------

@router.get(
    "/high-ticket-customers",
    response_model=HighTicketResponse,
    summary="Customers with high support ticket counts",
    description=(
        "Returns all customers whose support_tickets count exceeds `min_tickets`. "
        "Results are ordered by ticket count descending. "
        "High ticket volume is a leading indicator of dissatisfaction."
    ),
)
def analytics_high_ticket_customers(
    db: DB,
    min_tickets: int = Query(
        5,
        ge=1,
        le=50,
        description="Minimum number of support tickets to qualify (exclusive threshold)",
    ),
):
    """Fetch customers with more than min_tickets open/closed support tickets."""
    logger.info("GET /analytics/high-ticket-customers  min_tickets=%d", min_tickets)
    try:
        customers = crud.get_high_ticket_customers(db, min_tickets=min_tickets)
    except Exception as exc:
        logger.exception("Error fetching high-ticket customers")
        raise HTTPException(status_code=500, detail="Failed to fetch high-ticket customers") from exc

    return HighTicketResponse(
        min_tickets=min_tickets,
        count=len(customers),
        results=[CustomerResponse.model_validate(c) for c in customers],
    )


# ---------------------------------------------------------------------------
# GET /analytics/high-risk
# ---------------------------------------------------------------------------

@router.get(
    "/high-risk",
    response_model=HighRiskResponse,
    summary="High churn-risk customers (rule-based)",
    description=(
        "Identifies active (non-churned) customers at high risk of churning using "
        "a rule-based heuristic. A customer is flagged if they satisfy **at least 2** "
        "of the following conditions:\n\n"
        "- `support_tickets > 5`\n"
        "- `satisfaction_score < 5.0`\n"
        "- `last_login_days > 30`\n\n"
        "Results are ordered by satisfaction_score ascending (most at-risk first). "
        "This heuristic will be replaced by an ML model in Phase 4."
    ),
)
def analytics_high_risk(
    db: DB,
    limit: int = Query(50, ge=1, le=500, description="Maximum number of high-risk customers to return"),
):
    """Return high churn-risk customers identified by the rule-based heuristic."""
    logger.info("GET /analytics/high-risk  limit=%d", limit)
    try:
        customers = crud.get_high_risk_customers(db, limit=limit)
    except Exception as exc:
        logger.exception("Error fetching high-risk customers")
        raise HTTPException(status_code=500, detail="Failed to fetch high-risk customers") from exc

    return HighRiskResponse(
        limit=limit,
        count=len(customers),
        results=[CustomerResponse.model_validate(c) for c in customers],
    )
