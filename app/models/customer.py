"""
Customer ORM model — maps to the 'customers' table in SQLite.
"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Customer(Base):
    """
    Represents a customer record with churn-related attributes.
    All fields match the assessment requirements.
    """
    __tablename__ = "customers"

    # Primary key — human-readable ID like "C001", "C002"
    customer_id: Mapped[str] = mapped_column(String(20), primary_key=True, index=True)

    # Demographics
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(150), unique=True, nullable=False, index=True)
    age: Mapped[int] = mapped_column(Integer, nullable=False)

    # Subscription details
    plan: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    monthly_spend: Mapped[float] = mapped_column(Float, nullable=False)
    tenure_months: Mapped[int] = mapped_column(Integer, nullable=False)

    # Engagement metrics
    support_tickets: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_login_days: Mapped[int] = mapped_column(Integer, nullable=False)
    satisfaction_score: Mapped[float] = mapped_column(Float, nullable=False)  # 1.0 – 10.0

    # Churn label (ground truth for ML in Phase 4)
    churn: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Audit timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<Customer id={self.customer_id} plan={self.plan} churn={self.churn}>"
