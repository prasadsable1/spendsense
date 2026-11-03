import json
import uuid
from datetime import date

import pytest
from fastapi.testclient import TestClient

import app.database as database
from app.main import app


@pytest.fixture
def sqlite_api(tmp_path, monkeypatch):
    database._engine = None
    database._session_factory = None
    db_path = tmp_path / "spendsense-test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("APP_AUTH_REQUIRED", "false")
    monkeypatch.delenv("APP_ENV", raising=False)
    try:
        with TestClient(app) as client:
            yield client
    finally:
        if database._engine is not None:
            database._engine.dispose()
        database._engine = None
        database._session_factory = None


def create_transaction(client, category_id, *, day, amount, description, kind="expense"):
    response = client.post(
        "/api/transactions",
        json={
            "date": day.isoformat(),
            "amount": amount,
            "type": kind,
            "description": description,
            "merchant": "SQLite integration",
            "payment_method": "Card",
            "category_id": category_id,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_sqlite_health_crud_month_filters_and_dashboard(sqlite_api):
    client = sqlite_api
    suffix = uuid.uuid4().hex[:8]
    categories = client.get("/api/categories").json()
    category_id = next(item["id"] for item in categories if item["name"] == "Food")
    today = date.today()
    transaction = create_transaction(
        client,
        category_id,
        day=today,
        amount=42.75,
        description=f"SQLite current {suffix}",
    )
    create_transaction(
        client,
        category_id,
        day=date(today.year - 1, today.month, 15),
        amount=19.25,
        description=f"SQLite previous {suffix}",
    )

    assert client.get("/api/health").json() == {
        "status": "ok",
        "database": "connected",
    }
    filtered = client.get(
        "/api/transactions",
        params={"year": today.year, "month": today.month, "search": suffix},
    )
    assert filtered.status_code == 200
    assert [item["id"] for item in filtered.json()] == [transaction["id"]]
    month_only = client.get(
        "/api/transactions", params={"month": today.month, "search": suffix}
    )
    assert month_only.status_code == 200
    assert len(month_only.json()) == 2
    dashboard = client.get(
        "/api/dashboard", params={"year": today.year, "month": today.month}
    )
    assert dashboard.status_code == 200, dashboard.text
    assert dashboard.json()["total_expenses"] == 42.75

    updated = client.put(
        f"/api/transactions/{transaction['id']}",
        json={
            "date": today.isoformat(),
            "amount": 55.25,
            "type": "expense",
            "description": f"SQLite current {suffix}",
            "merchant": "SQLite integration",
            "payment_method": "Cash",
            "category_id": category_id,
        },
    )
    assert updated.status_code == 200
    assert float(updated.json()["amount"]) == 55.25
    assert client.delete(f"/api/transactions/{transaction['id']}").status_code == 204


def test_sqlite_budgets_analytics_monthly_report_and_csv(sqlite_api):
    client = sqlite_api
    categories = client.get("/api/categories").json()
    category_id = next(item["id"] for item in categories if item["name"] == "Food")
    today = date.today()
    create_transaction(
        client, category_id, day=today, amount=80, description="SQLite budget expense"
    )
    create_transaction(
        client,
        category_id,
        day=today,
        amount=150,
        description="SQLite budget income",
        kind="income",
    )
    budget = client.post(
        "/api/budgets",
        json={
            "year": today.year,
            "month": today.month,
            "amount": 100,
            "category_id": category_id,
        },
    )
    assert budget.status_code == 201, budget.text
    assert budget.json()["percent_used"] == 80
    assert budget.json()["status"] == "warning"

    report = client.get(
        "/api/reports/monthly",
        params={"year": today.year, "month": today.month},
    )
    assert report.status_code == 200, report.text
    assert report.json()["transaction_count"] == 2
    analytics = client.get("/api/analytics")
    assert analytics.status_code == 200
    assert analytics.json()["total_expenses"] == 80
    export = client.get("/api/reports/export")
    assert export.status_code == 200
    assert "SQLite budget expense" in export.text


def test_sqlite_csv_import_duplicate_detection_and_ml_response(sqlite_api):
    client = sqlite_api
    categories = client.get("/api/categories").json()
    category_id = next(item["id"] for item in categories if item["name"] == "Food")
    contents = b"date,description,amount,merchant\n2025-01-02,Coffee,5.50,Cafe\n"
    preview = client.post(
        "/api/imports/preview",
        files={"file": ("sample.csv", contents, "text/csv")},
    )
    assert preview.status_code == 200, preview.text
    mapping = preview.json()["suggested_mapping"]
    form = {"mapping": json.dumps(mapping), "category_id": str(category_id)}
    imported = client.post(
        "/api/imports/confirm",
        data=form,
        files={"file": ("sample.csv", contents, "text/csv")},
    )
    assert imported.status_code == 200, imported.text
    assert imported.json()["imported"] == 1
    duplicate = client.post(
        "/api/imports/confirm",
        data=form,
        files={"file": ("sample.csv", contents, "text/csv")},
    )
    assert duplicate.status_code == 200
    assert duplicate.json()["duplicates"] == 1

    predictions = client.get("/api/predictions")
    assert predictions.status_code == 200
    assert predictions.json()["available"] is False
    assert "6 distinct months" in predictions.json()["reason"]
    assert client.get("/api/anomalies").status_code == 200
