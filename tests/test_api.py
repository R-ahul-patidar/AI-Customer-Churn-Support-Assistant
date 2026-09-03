import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_get_customers_paginated():
    response = client.get("/customers?page=1&page_size=10")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "results" in data
    assert len(data["results"]) <= 10
    if data["results"]:
        first = data["results"][0]
        assert "customer_id" in first
        assert "plan" in first
        assert "email" in first
        assert "monthly_spend" in first


def test_get_customer_detail():
    list_res = client.get("/customers?page_size=1")
    assert list_res.status_code == 200
    results = list_res.json()["results"]
    if results:
        cid = results[0]["customer_id"]
        res = client.get(f"/customers/{cid}")
        assert res.status_code == 200
        assert res.json()["customer_id"] == cid


def test_get_customer_not_found():
    res = client.get("/customers/NON_EXISTENT_ID_9999")
    assert res.status_code == 404


def test_get_analytics_consolidated():
    response = client.get("/analytics")
    assert response.status_code == 200
    data = response.json()
    assert "summary" in data
    assert "churn_by_plan" in data
    assert "avg_spend_by_plan" in data
    assert "top_spenders" in data


def test_get_analytics_summary():
    response = client.get("/analytics/summary")
    assert response.status_code == 200
    data = response.json()
    assert "total_customers" in data
    assert "churn_rate" in data
    assert "high_risk_count" in data


def test_get_analytics_churn_by_plan():
    response = client.get("/analytics/churn-by-plan")
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert len(data["results"]) > 0


def test_get_analytics_high_risk():
    response = client.get("/analytics/high-risk?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert len(data["results"]) <= 5


def test_predict_churn_endpoint():
    payload = {
        "age": 35,
        "plan": "Basic",
        "monthly_spend": 49.99,
        "tenure_months": 2,
        "support_tickets": 7,
        "last_login_days": 50,
        "satisfaction_score": 2.5,
    }
    response = client.post("/predict-churn", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "churn_probability" in data
    assert data["risk"] in ["LOW", "MEDIUM", "HIGH"]
    assert len(data["risk_factors"]) > 0
