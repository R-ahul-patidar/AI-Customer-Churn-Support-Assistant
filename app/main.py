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
from app.routers import customers

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
        "Phase 1: Customer CRUD and data layer."
    ),
    version="0.1.0",
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

# Phase 2 — analytics router (added in next phase)
# from app.routers import analytics
# app.include_router(analytics.router)

# Phase 3 — AI assistant router (added in next phase)
# from app.routers import assistant
# app.include_router(assistant.router)


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
