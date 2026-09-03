"""
FastAPI application entry point.
Creates the app, registers middleware, and includes all routers.
"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine
from app.models import customer  # noqa: F401 — ensures model is registered with Base
from app.models.customer import Base
from app.routers import analytics, assistant, customers
from app.schemas.analytics import PredictChurnRequest, PredictChurnResponse

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Create tables (development convenience — Alembic handles this in production)
# ---------------------------------------------------------------------------
Base.metadata.create_all(bind=engine)

# ---------------------------------------------------------------------------
# App instance
# ---------------------------------------------------------------------------
app = FastAPI(
    title="AI Customer Churn & Support Assistant",
    description=(
        "Backend API for customer churn analytics and AI-powered support. "
        "Phase 3: AI assistant (POST /ask) powered by LangChain SQL Agent + Google Gemini. "
        "Ask any natural-language question about your customer data."
    ),
    version="0.3.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ---------------------------------------------------------------------------
# CORS — allow all origins in development; tighten in production
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(customers.router)

# Phase 2 — analytics endpoints
app.include_router(analytics.router)

# Phase 3 — AI assistant (POST /ask)
app.include_router(assistant.router)


# ---------------------------------------------------------------------------
# Assessment Endpoint: POST /predict-churn (Rule-Based Risk Scoring)
# ---------------------------------------------------------------------------
@app.post(
    "/predict-churn",
    response_model=PredictChurnResponse,
    tags=["Prediction"],
    summary="Predict customer churn probability and risk tier",
    description=(
        "Calculates churn probability and classifies risk as LOW, MEDIUM, or HIGH "
        "using a deterministic multi-factor risk model matching assessment requirements."
    ),
)
def predict_churn(payload: PredictChurnRequest):
    factors = []
    score = 0.15  # Base probability

    if payload.satisfaction_score < 4.0:
        score += 0.35
        factors.append("Critically low satisfaction score (< 4.0)")
    elif payload.satisfaction_score < 6.0:
        score += 0.15
        factors.append("Sub-optimal satisfaction score (< 6.0)")

    if payload.support_tickets > 5:
        score += 0.30
        factors.append(f"High support ticket volume ({payload.support_tickets} tickets)")
    elif payload.support_tickets > 3:
        score += 0.15
        factors.append(f"Elevated support tickets ({payload.support_tickets} tickets)")

    if payload.last_login_days > 45:
        score += 0.30
        factors.append(f"Prolonged inactivity ({payload.last_login_days} days since last login)")
    elif payload.last_login_days > 20:
        score += 0.15
        factors.append(f"Moderate inactivity ({payload.last_login_days} days)")

    if payload.tenure_months < 3:
        score += 0.10
        factors.append("New account (< 3 months tenure)")

    prob = min(max(round(score, 2), 0.05), 0.95)
    if prob >= 0.60:
        risk = "HIGH"
    elif prob >= 0.30:
        risk = "MEDIUM"
    else:
        risk = "LOW"

    return PredictChurnResponse(
        churn_probability=prob,
        risk=risk,
        risk_factors=factors,
    )


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get("/health", tags=["Health"], summary="Health check")
def health_check():
    """Returns application status and version. Used for uptime monitoring."""
    return {
        "status": "ok",
        "version": app.version,
        "environment": settings.app_env,
    }


@app.get("/", tags=["Health"], summary="Root")
def root():
    """Redirects to API docs."""
    return {
        "message": "AI Customer Churn & Support Assistant API",
        "docs": "/docs",
        "health": "/health",
    }
