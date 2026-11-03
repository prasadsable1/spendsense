import json
import os
import uuid
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import get_session_factory
from app.auth import hash_password
from app.main import app
from app.models import ImportHistory


MYSQL_CONFIGURED = all(
    os.environ.get(key) for key in ("DB_USER", "DB_PASSWORD", "DB_NAME")
)

pytestmark = pytest.mark.skipif(
    not MYSQL_CONFIGURED,
    reason="Configure backend/.env to run live MySQL integration tests.",
)


@pytest.fixture
def mysql_api():
    suffix = uuid.uuid4().hex[:12]
    with TestClient(app) as client:
        category_response = client.post(
            "/api/categories",
            json={"name": f"Integration {suffix}", "color": "#7186ff"},
        )
        assert category_response.status_code == 201, category_response.text
        category = category_response.json()
        state = {
            "category_id": category["id"],
            "transaction_ids": [],
            "budget_ids": [],
            "import_filenames": [],
            "suffix": suffix,
        }
        try:
            yield client, state
        finally:
            for transaction_id in reversed(state["transaction_ids"]):
                response = client.delete(f"/api/transactions/{transaction_id}")
                assert response.status_code in (204, 404), response.text
            for budget_id in reversed(state["budget_ids"]):
                response = client.delete(f"/api/budgets/{budget_id}")
                assert response.status_code in (204, 404), response.text
            response = client.delete(f"/api/categories/{state['category_id']}")
            assert response.status_code == 204, response.text
            with get_session_factory()() as db:
                records = db.scalars(
                    select(ImportHistory).where(
                        ImportHistory.filename.in_(state["import_filenames"])
                    )
                ).all()
                for record in records:
                    db.delete(record)
                db.commit()


def _create_transaction(client, state, *, day: date, amount: float, description: str, kind: str = "expense"):
    response = client.post(
        "/api/transactions",
        json={
            "date": day.isoformat(),
            "amount": amount,
            "type": kind,
            "description": description,
            "merchant": f"Integration {state['suffix']}",
            "payment_method": "Card",
            "category_id": state["category_id"],
        },
    )
    assert response.status_code == 201, response.text
    transaction = response.json()
    state["transaction_ids"].append(transaction["id"])
    return transaction


def _month_date(offset: int) -> date:
    absolute_month = date.today().year * 12 + date.today().month - 1 - offset
    year, month_zero_based = divmod(absolute_month, 12)
    return date(year, month_zero_based + 1, 15)


def test_mysql_transaction_crud_filters_categories_and_validation(mysql_api):
    client, state = mysql_api
    assert client.get("/api/health").json()["database"] == "connected"
    assert len(client.get("/api/categories").json()) >= 10

    transaction = _create_transaction(
        client,
        state,
        day=date.today(),
        amount=12.34,
        description=f"Searchable integration {state['suffix']}",
    )
    update = client.put(
        f"/api/transactions/{transaction['id']}",
        json={
            "date": date.today().isoformat(),
            "amount": 20.25,
            "type": "expense",
            "description": f"Searchable integration {state['suffix']}",
            "merchant": f"Integration {state['suffix']}",
            "payment_method": "Cash",
            "category_id": state["category_id"],
        },
    )
    assert update.status_code == 200, update.text
    assert float(update.json()["amount"]) == 20.25
    search = client.get(
        "/api/transactions",
        params={"search": state["suffix"], "limit": 1, "offset": 0, "sort": "amount"},
    )
    assert search.status_code == 200 and search.json()[0]["id"] == transaction["id"]
    count = client.get("/api/transactions/count", params={"search": state["suffix"]})
    assert count.json()["count"] == 1
    assert client.post(
        "/api/transactions",
        json={
            "date": date.today().isoformat(),
            "amount": 1,
            "type": "expense",
            "description": "Bad category",
            "category_id": 99999999,
        },
    ).status_code == 422
    assert client.delete(f"/api/categories/{state['category_id']}").status_code == 409

    deleted = client.delete(f"/api/transactions/{transaction['id']}")
    assert deleted.status_code == 204
    state["transaction_ids"].remove(transaction["id"])
    assert client.delete(f"/api/transactions/{transaction['id']}").status_code == 404


def test_mysql_budgets_dashboard_and_monthly_and_csv_reports(mysql_api):
    client, state = mysql_api
    today = date.today()
    for offset, amount in ((0, 100), (1, 100)):
        _create_transaction(
            client,
            state,
            day=_month_date(offset),
            amount=amount,
            description=f"Budget report {state['suffix']} {offset}",
        )
    _create_transaction(
        client,
        state,
        day=today,
        amount=200,
        kind="income",
        description=f"Report income {state['suffix']}",
    )

    budget = client.post(
        "/api/budgets",
        json={
            "year": today.year,
            "month": today.month,
            "amount": 125,
            "category_id": state["category_id"],
        },
    )
    assert budget.status_code == 201, budget.text
    budget_data = budget.json()
    state["budget_ids"].append(budget_data["id"])
    assert budget_data["status"] == "warning"
    assert budget_data["percent_used"] == 80

    dashboard = client.get(
        "/api/dashboard", params={"year": today.year, "month": today.month}
    )
    assert dashboard.status_code == 200, dashboard.text
    assert dashboard.json()["total_expenses"] >= 100
    assert dashboard.json()["total_income"] >= 200
    assert any(item["category_name"] == f"Integration {state['suffix']}" for item in dashboard.json()["budgets"])

    report = client.get(
        "/api/reports/monthly", params={"year": today.year, "month": today.month}
    )
    assert report.status_code == 200, report.text
    assert report.json()["transaction_count"] >= 2
    monthly_export = client.get(
        "/api/reports/export",
        params={"year": today.year, "month": today.month},
    )
    full_export = client.get("/api/reports/export")
    assert monthly_export.status_code == full_export.status_code == 200
    assert "text/csv" in monthly_export.headers["content-type"]
    assert f"Report income {state['suffix']}" in full_export.text


def test_mysql_csv_mapping_duplicate_detection_and_validation(mysql_api):
    client, state = mysql_api
    filename = f"spendsense-integration-{state['suffix']}.csv"
    state["import_filenames"].append(filename)
    content = (
        "Posted Date,Details,Withdrawal,Deposit,Payee\n"
        f"{date.today().isoformat()},Debit {state['suffix']},12.25,,Test merchant\n"
        f"{date.today().isoformat()},Credit {state['suffix']},,45.50,Test payer\n"
    ).encode()
    files = {"file": (filename, content, "text/csv")}
    preview = client.post("/api/imports/preview", files=files)
    assert preview.status_code == 200, preview.text
    mapping = preview.json()["suggested_mapping"]
    assert mapping["date"] == "Posted Date"
    assert mapping["debit"] == "Withdrawal"
    assert mapping["credit"] == "Deposit"
    form = {
        "mapping": json.dumps(mapping),
        "category_id": str(state["category_id"]),
    }

    imported = client.post("/api/imports/confirm", files=files, data=form)
    assert imported.status_code == 200, imported.text
    assert imported.json()["imported"] == 2
    assert imported.json()["duplicates"] == 0
    transactions = client.get(
        "/api/transactions", params={"search": state["suffix"], "limit": 500}
    )
    assert transactions.status_code == 200, transactions.text
    for transaction in transactions.json():
        if transaction["description"] in {
            f"Debit {state['suffix']}",
            f"Credit {state['suffix']}",
        }:
            state["transaction_ids"].append(transaction["id"])
    imported_types = {
        row["description"]: row["type"]
        for row in transactions.json()
        if row["description"] in {f"Debit {state['suffix']}", f"Credit {state['suffix']}"}
    }
    assert imported_types == {
        f"Debit {state['suffix']}": "expense",
        f"Credit {state['suffix']}": "income",
    }

    duplicate = client.post("/api/imports/confirm", files=files, data=form)
    assert duplicate.status_code == 200, duplicate.text
    assert duplicate.json()["imported"] == 0
    assert duplicate.json()["duplicates"] == 2
    assert client.post(
        "/api/imports/preview",
        files={"file": ("bad.txt", b"not a CSV file", "text/plain")},
    ).status_code == 400
    bad_csv = client.post(
        "/api/imports/confirm",
        files={
            "file": (
                "invalid-date.csv",
                b"date,description,amount\ninvalid,Test,1\n",
                "text/csv",
            )
        },
        data={
            "mapping": json.dumps(
                {"date": "date", "description": "description", "amount": "amount"}
            )
        },
    )
    assert bad_csv.status_code == 422


def test_mysql_analytics_chronological_forecast_and_anomaly_detection(mysql_api):
    client, state = mysql_api
    monthly_amounts = [90, 100, 110, 95, 120, 105, 100, 100]
    for offset, amount in zip(range(7, -1, -1), monthly_amounts):
        _create_transaction(
            client,
            state,
            day=_month_date(offset),
            amount=amount,
            description=f"Forecast history {state['suffix']} {offset}",
        )
    unusual = _create_transaction(
        client,
        state,
        day=date.today(),
        amount=500,
        description=f"Unusual {state['suffix']}",
    )
    _create_transaction(
        client,
        state,
        day=date.today(),
        amount=200,
        kind="income",
        description=f"Forecast income {state['suffix']}",
    )

    analytics = client.get("/api/analytics")
    assert analytics.status_code == 200, analytics.text
    assert len(analytics.json()["monthly"]) >= 8
    assert any(comparison["change"] > 0 for comparison in analytics.json()["comparisons"])

    prediction = client.get("/api/predictions")
    assert prediction.status_code == 200, prediction.text
    assert prediction.json()["available"] is True
    assert prediction.json()["mae"] >= 0
    assert len(prediction.json()["evaluation"]) >= 2
    assert prediction.json()["next_month"] > prediction.json()["historical"][-1]["month"]

    anomaly_response = client.get("/api/anomalies")
    assert anomaly_response.status_code == 200, anomaly_response.text
    assert any(
        row["id"] == unusual["id"]
        for row in anomaly_response.json()["transactions"]
    )
    assert any(
        increase["month"] == date.today().strftime("%Y-%m")
        for increase in anomaly_response.json()["spending_increases"]
    )


def test_mysql_api_authentication_protects_financial_endpoints(mysql_api, monkeypatch):
    client, _ = mysql_api
    app_password = "Integration password with enough length"
    monkeypatch.setenv("APP_AUTH_REQUIRED", "true")
    monkeypatch.setenv("APP_SECRET_KEY", "integration-signing-key-that-is-at-least-32-chars")
    monkeypatch.setenv("APP_PASSWORD_HASH", hash_password(app_password))

    assert client.get("/api/auth/status").json() == {"required": True}
    assert client.get("/api/health").status_code == 200
    assert client.get("/api/categories").status_code == 401
    assert client.post("/api/auth/login", json={"password": "incorrect password"}).status_code == 401

    login = client.post("/api/auth/login", json={"password": app_password})
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    assert login.json()["token_type"] == "bearer"

    categories = client.get(
        "/api/categories", headers={"Authorization": f"Bearer {token}"}
    )
    assert categories.status_code == 200, categories.text

    monkeypatch.setenv("APP_SECRET_KEY", "rotated-signing-key-that-is-at-least-32-characters")
    assert client.get(
        "/api/categories", headers={"Authorization": f"Bearer {token}"}
    ).status_code == 401
