"""
Pydantic v2 schemas for Customer request/response validation.
Separating ORM models from API schemas keeps the API contract stable
even when internal DB schema evolves.
"""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ---------------------------------------------------------------------------
# Shared field definitions
# ---------------------------------------------------------------------------

PLAN_TYPES = Literal["Basic", "Standard", "Premium"]


# ---------------------------------------------------------------------------
# Response schemas (what the API returns)
# ---------------------------------------------------------------------------

class CustomerBase(BaseModel):
    """Fields shared between create and read schemas."""
    customer_id: str
    name: str
    email: EmailStr
    age: int = Field(..., ge=18, le=100)
    plan: PLAN_TYPES
    monthly_spend: float = Field(..., ge=0)
    tenure_months: int = Field(..., ge=0)
    support_tickets: int = Field(..., ge=0)
    last_login_days: int = Field(..., ge=0)
    satisfaction_score: float = Field(..., ge=1.0, le=10.0)
    churn: bool


class CustomerResponse(CustomerBase):
    """Full customer record returned by the API."""
    created_at: datetime
    updated_at: datetime

    # Allow ORM model instances to be passed directly
    model_config = ConfigDict(from_attributes=True)


class CustomerSummary(BaseModel):
    """Lightweight customer record for list responses."""
    customer_id: str
    name: str
    plan: PLAN_TYPES
    monthly_spend: float
    churn: bool
    satisfaction_score: float

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Paginated list response
# ---------------------------------------------------------------------------

class PaginatedCustomers(BaseModel):
    """Wrapper for paginated list endpoints."""
    total: int
    page: int
    page_size: int
    results: list[CustomerSummary]


# ---------------------------------------------------------------------------
# Query / filter params (used as FastAPI query dependencies)
# ---------------------------------------------------------------------------

class CustomerFilters(BaseModel):
    """Optional filters for GET /customers."""
    plan: Optional[PLAN_TYPES] = None
    churn: Optional[bool] = None
    min_spend: Optional[float] = None
    max_spend: Optional[float] = None
    search: Optional[str] = Field(
        None,
        description="Search by name, email, or customer_id (case-insensitive)",
    )
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)
