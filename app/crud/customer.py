"""
Customer CRUD operations and SQL analytics queries.
All database interactions are centralised here — routers stay thin.
"""
from typing import Optional

from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.schemas.customer import CustomerFilters


# ---------------------------------------------------------------------------
# Basic CRUD
# ---------------------------------------------------------------------------

def get_customer_by_id(db: Session, customer_id: str) -> Optional[Customer]:
    """Fetch a single customer by their ID. Returns None if not found."""
    return db.query(Customer).filter(Customer.customer_id == customer_id).first()


def get_customers(db: Session, filters: CustomerFilters) -> tuple[list[Customer], int]:
    """
    Return a paginated list of customers with optional filters.

    Returns:
        (customers, total_count) — the page of results and total matching rows.
    """
    query = db.query(Customer)

    # Apply optional filters
    if filters.plan:
        query = query.filter(Customer.plan == filters.plan)

    if filters.churn is not None:
        query = query.filter(Customer.churn == filters.churn)

    if filters.min_spend is not None:
        query = query.filter(Customer.monthly_spend >= filters.min_spend)

    if filters.max_spend is not None:
        query = query.filter(Customer.monthly_spend <= filters.max_spend)

    if filters.search:
        search_term = f"%{filters.search.lower()}%"
        query = query.filter(
            (func.lower(Customer.name).like(search_term))
            | (func.lower(Customer.email).like(search_term))
            | (func.lower(Customer.customer_id).like(search_term))
        )

    total = query.count()

    # Pagination
    offset = (filters.page - 1) * filters.page_size
    customers = (
        query.order_by(Customer.customer_id)
        .offset(offset)
        .limit(filters.page_size)
        .all()
    )

    return customers, total


# ---------------------------------------------------------------------------
# Analytics SQL queries
# ---------------------------------------------------------------------------

def get_top_spenders(db: Session, limit: int = 10) -> list[Customer]:
    """Top N customers ordered by monthly spend descending."""
    return (
        db.query(Customer)
        .order_by(Customer.monthly_spend.desc())
        .limit(limit)
        .all()
    )


def get_avg_spend_by_plan(db: Session) -> list[dict]:
    """Average monthly spend grouped by plan."""
    rows = (
        db.query(
            Customer.plan,
            func.round(func.avg(Customer.monthly_spend), 2).label("avg_spend"),
            func.count(Customer.customer_id).label("customer_count"),
        )
        .group_by(Customer.plan)
        .order_by(func.avg(Customer.monthly_spend).desc())
        .all()
    )
    return [{"plan": r.plan, "avg_spend": r.avg_spend, "customer_count": r.customer_count} for r in rows]


def get_high_ticket_customers(db: Session, min_tickets: int = 5) -> list[Customer]:
    """Customers with more than `min_tickets` support tickets."""
    return (
        db.query(Customer)
        .filter(Customer.support_tickets > min_tickets)
        .order_by(Customer.support_tickets.desc())
        .all()
    )


def get_churn_rate_by_plan(db: Session) -> list[dict]:
    """
    Churn rate per plan: number of churned customers / total customers.
    Uses SQLAlchemy Core for a raw-SQL-style aggregation query.
    """
    rows = (
        db.query(
            Customer.plan,
            func.count(Customer.customer_id).label("total"),
        )
        .group_by(Customer.plan)
        .all()
    )

    # Compute churn_rate in Python to avoid SQLite dialect issues with division
    result = []
    for r in rows:
        # Re-query churned count cleanly
        churned = (
            db.query(func.count(Customer.customer_id))
            .filter(Customer.plan == r.plan, Customer.churn == True)  # noqa: E712
            .scalar()
        ) or 0
        total = r.total or 1
        result.append(
            {
                "plan": r.plan,
                "total_customers": total,
                "churned_customers": churned,
                "churn_rate": round(churned / total * 100, 2),
            }
        )

    return sorted(result, key=lambda x: x["churn_rate"], reverse=True)


def get_high_risk_customers(db: Session, limit: int = 50) -> list[Customer]:
    """
    Rule-based high churn-risk customers (no ML required).
    A customer is flagged as high-risk if they meet 2 or more of:
      - support_tickets > 5
      - satisfaction_score < 5.0
      - last_login_days > 30
    Uses SQLite-compatible approach with sqlalchemy.case for boolean summation.
    This heuristic will be replaced by the ML model in Phase 4.
    """
    from sqlalchemy import case

    risk_score = (
        case((Customer.support_tickets > 5, 1), else_=0)
        + case((Customer.satisfaction_score < 5.0, 1), else_=0)
        + case((Customer.last_login_days > 30, 1), else_=0)
    )

    return (
        db.query(Customer)
        .filter(Customer.churn == False)  # noqa: E712 — not yet churned but at risk
        .filter(risk_score >= 2)
        .order_by(Customer.satisfaction_score.asc())
        .limit(limit)
        .all()
    )


def get_summary_stats(db: Session) -> dict:
    """
    Dashboard summary: total customers, churn rate, avg spend, high-risk count.
    Used by GET /analytics/summary.
    """
    total = db.query(func.count(Customer.customer_id)).scalar() or 0
    churned = (
        db.query(func.count(Customer.customer_id))
        .filter(Customer.churn == True)  # noqa: E712
        .scalar()
    ) or 0
    avg_spend = (
        db.query(func.round(func.avg(Customer.monthly_spend), 2)).scalar()
    ) or 0.0
    high_risk = get_high_risk_customers(db, limit=10000)

    return {
        "total_customers": total,
        "churned_customers": churned,
        "churn_rate": round(churned / total * 100, 2) if total else 0.0,
        "avg_monthly_spend": avg_spend,
        "high_risk_count": len(high_risk),
    }
