"""
Pydantic v2 response schemas for analytics endpoints.
Each schema maps 1-to-1 with an analytics CRUD function's return shape so the
API contract is explicit and self-documenting via FastAPI's OpenAPI output.
"""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.customer import CustomerResponse, PLAN_TYPES


# ---------------------------------------------------------------------------
# /analytics/summary
# ---------------------------------------------------------------------------

class SummaryStats(BaseModel):
    """High-level dashboard figures returned by GET /analytics/summary."""
    total_customers: int = Field(..., description="Total number of customers in the database")
    churned_customers: int = Field(..., description="Number of customers who have churned")
    churn_rate: float = Field(..., description="Overall churn rate as a percentage (0–100)")
    avg_monthly_spend: float = Field(..., description="Average monthly spend across all customers (USD)")
    high_risk_count: int = Field(..., description="Number of active customers flagged as high churn-risk")


# ---------------------------------------------------------------------------
# /analytics/top-spenders
# ---------------------------------------------------------------------------

class TopSpendersResponse(BaseModel):
    """Response envelope for GET /analytics/top-spenders."""
    limit: int = Field(..., description="Number of top spenders returned")
    results: list[CustomerResponse]


# ---------------------------------------------------------------------------
# /analytics/churn-by-plan
# ---------------------------------------------------------------------------

class ChurnByPlanItem(BaseModel):
    """Churn statistics for a single subscription plan."""
    plan: PLAN_TYPES
    total_customers: int
    churned_customers: int
    churn_rate: float = Field(..., description="Churn rate for this plan as a percentage (0–100)")


class ChurnByPlanResponse(BaseModel):
    """Response envelope for GET /analytics/churn-by-plan."""
    results: list[ChurnByPlanItem]


# ---------------------------------------------------------------------------
# /analytics/high-ticket-customers
# ---------------------------------------------------------------------------

class HighTicketResponse(BaseModel):
    """Response envelope for GET /analytics/high-ticket-customers."""
    min_tickets: int = Field(..., description="Minimum support ticket threshold used for filtering")
    count: int = Field(..., description="Total number of matching customers")
    results: list[CustomerResponse]


# ---------------------------------------------------------------------------
# /analytics/high-risk
# ---------------------------------------------------------------------------

class HighRiskResponse(BaseModel):
    """Response envelope for GET /analytics/high-risk."""
    limit: int = Field(..., description="Maximum number of high-risk customers returned")
    count: int = Field(..., description="Number of high-risk customers in this response")
    rule: str = Field(
        default=(
            "Customer meets ≥2 of: support_tickets > 5, "
            "satisfaction_score < 5.0, last_login_days > 30"
        ),
        description="Rule used to classify a customer as high-risk",
    )
    results: list[CustomerResponse]


# ---------------------------------------------------------------------------
# /analytics/avg-spend-by-plan
# ---------------------------------------------------------------------------

class AvgSpendByPlanItem(BaseModel):
    """Average spend statistics for a single subscription plan."""
    plan: PLAN_TYPES
    avg_spend: float = Field(..., description="Average monthly spend for this plan (USD)")
    customer_count: int = Field(..., description="Number of customers on this plan")


class AvgSpendByPlanResponse(BaseModel):
    """Response envelope for GET /analytics/avg-spend-by-plan."""
    results: list[AvgSpendByPlanItem]
