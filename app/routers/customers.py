"""
Customer router — GET /customers and GET /customers/{customer_id}
"""
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.crud import customer as crud
from app.database import get_db
from app.schemas.customer import (
    CustomerFilters,
    CustomerResponse,
    PaginatedCustomers,
)

router = APIRouter(prefix="/customers", tags=["Customers"])

DbDep = Annotated[Session, Depends(get_db)]


@router.get(
    "",
    response_model=PaginatedCustomers,
    summary="List / search customers",
    description=(
        "Returns a paginated list of customers. "
        "Supports filtering by plan, churn status, spend range, and free-text search."
    ),
)
def list_customers(
    db: DbDep,
    plan: Optional[str] = Query(None, description="Filter by plan: Basic, Standard, or Premium"),
    churn: Optional[bool] = Query(None, description="Filter by churn status"),
    min_spend: Optional[float] = Query(None, ge=0, description="Minimum monthly spend"),
    max_spend: Optional[float] = Query(None, ge=0, description="Maximum monthly spend"),
    search: Optional[str] = Query(None, description="Search by name, email, or customer ID"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Results per page"),
):
    filters = CustomerFilters(
        plan=plan,
        churn=churn,
        min_spend=min_spend,
        max_spend=max_spend,
        search=search,
        page=page,
        page_size=page_size,
    )
    customers, total = crud.get_customers(db, filters)
    return PaginatedCustomers(
        total=total,
        page=page,
        page_size=page_size,
        results=customers,
    )


@router.get(
    "/{customer_id}",
    response_model=CustomerResponse,
    summary="Get customer by ID",
    description="Returns full details for a single customer including all churn-related metrics.",
    responses={
        404: {"description": "Customer not found"},
    },
)
def get_customer(customer_id: str, db: DbDep):
    customer = crud.get_customer_by_id(db, customer_id)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer '{customer_id}' not found.",
        )
    return customer
