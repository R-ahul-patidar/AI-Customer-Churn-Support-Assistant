# AI-Customer-Churn-Support-Assistant

AI-powered customer churn analytics and support assistant using FastAPI, SQLite/SQLAlchemy, and LangChain with Google Gemini.

## Requirements & Dependencies

The backend requires Python 3.10+ (tested on Python 3.11, 3.12, and 3.14 on Windows).

### Core Dependencies
- **FastAPI & Uvicorn**: API framework and ASGI server
- **SQLAlchemy & Alembic**: Database ORM and migrations
- **Pydantic v2**: Request & response validation
- **Faker**: Synthetic customer data generation
- **LangChain & LangChain-Community**: LLM orchestration and SQL Database agent
- **LangChain-Google-GenAI**: Gemini integration via Google GenAI SDK
- **Streamlit**: Web-based analytical dashboard and chat interface

### Installation

```bash
# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\activate  # Windows

# Install all dependencies from requirements.txt
pip install -r requirements.txt
```

### Environment Configuration (.env)

Ensure your `.env` file contains your Google Gemini API key and model selection:

```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-3.6-flash
DATABASE_URL=sqlite:///./churn_assistant.db
API_BASE_URL=http://127.0.0.1:8000
```

### Running the Application

1. **Start the FastAPI Backend**:
```bash
.\venv\Scripts\uvicorn.exe app.main:app --reload --port 8000
```
Interactive API docs are available at `http://127.0.0.1:8000/docs`.

2. **Start the Streamlit Frontend**:
```bash
.\venv\Scripts\streamlit.exe run ui/app.py
```
Open your browser at `http://localhost:8501`.

### Frontend Views
- **📊 Analytics Dashboard**: Executive KPIs (total customers, churn rate, monthly spend, high-risk accounts) and interactive distribution charts by subscription plan.
- **👥 Customer Directory & Risk**: Search and filter accounts by name, email, plan, or churn status with instant churn-risk indicators.
- **💬 AI Support Assistant**: Ask questions in natural language. Powered by Gemini + LangChain SQL Agent for real-time customer analysis and dynamic queries with executed SQL display.

## Architecture

```
Streamlit UI (Port 8501)
       │
       ▼ REST API HTTP
FastAPI Backend (Port 8000)
       ├── /customers          ──> SQLite ORM (SQLAlchemy)
       ├── /analytics          ──> SQL Aggregations
       ├── /predict-churn      ──> Multi-Factor Risk Heuristic
       └── /ask                ──> LangChain SQL Agent + Google Gemini
                                         │
                                         ▼
                                SQLite Database (churn_assistant.db)
```

## API Endpoints Overview

| Method | Endpoint | Purpose |
| :--- | :--- | :--- |
| `GET` | `/health` | Application status and uptime check |
| `GET` | `/customers` | Paginated customer search and filtering (plan, churn, spend) |
| `GET` | `/customers/{id}` | Full customer profile and engagement metrics |
| `GET` | `/analytics` | Consolidated analytics payload (summary, plan churn, spend) |
| `GET` | `/analytics/summary` | Executive KPI stats (total, churn rate, avg spend, high-risk) |
| `GET` | `/analytics/top-spenders` | Top spenders ordered by monthly spend |
| `GET` | `/analytics/churn-by-plan` | Churn rates broken down by subscription tier |
| `GET` | `/analytics/avg-spend-by-plan`| Mean monthly spend by plan |
| `GET` | `/analytics/high-risk` | Active accounts meeting ≥2 churn risk criteria |
| `POST` | `/predict-churn` | Rule-based churn probability & risk tier calculation |
| `POST` | `/ask` | Natural-language query orchestrator with LangChain SQL Agent |

Interactive Swagger documentation is available at `http://127.0.0.1:8000/docs`.

## Standalone SQL Scripts (Deliverables)

The repository includes standalone SQL scripts for database setup and assessment queries:
- **`scripts/schema.sql`**: Full DDL script creating the `customers` table with constraints and indexes.
- **`scripts/queries.sql`**: The 5 required analytical queries (top spenders, spend by plan, high-ticket accounts, churn rate by plan, high churn-risk indicators).

## Running Automated Tests

Run the complete test suite:

```bash
.\venv\Scripts\pytest.exe tests -v
```

## Deployment Guide

1. **Backend (Render / Railway / Koyeb)**:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn app.main:app --host 0.0.0.0 --port 8000`
   - Environment Variables: Add `GEMINI_API_KEY`, `GEMINI_MODEL`, `DATABASE_URL=sqlite:///./churn_assistant.db`.
   - Run seed script on first launch: `python scripts/seed_data.py`.

2. **Frontend (Streamlit Community Cloud)**:
   - Deploy directly from your GitHub repository.
   - Main file path: `ui/app.py`.
   - Set secret: `API_BASE_URL=https://<your-backend-render-url>.onrender.com`.