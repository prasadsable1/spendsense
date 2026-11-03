from decimal import Decimal

from app.analytics import budget_usage, detect_anomalies, forecast_spending, spending_analytics, summarize_transactions


def test_summary_uses_real_period_transactions():
    rows = [
        {"date": "2026-03-01", "amount": 30, "type": "expense", "category": "Food"},
        {"date": "2026-03-02", "amount": 70, "type": "expense", "category": "Travel"},
        {"date": "2026-03-03", "amount": 200, "type": "income", "category": "Other"},
        {"date": "2026-02-28", "amount": 50, "type": "expense", "category": "Food"},
    ]
    result = summarize_transactions(rows, 2026, 3)
    assert result["total_expenses"] == 100
    assert result["total_income"] == 200
    assert result["savings_estimate"] == 100
    assert result["highest_category"] == {"name": "Travel", "amount": 70}
    assert result["median_transaction"] == 50


def test_empty_summary_has_zero_totals_and_no_date_accessor_errors():
    result = summarize_transactions([], 2026, 3)
    assert result["total_expenses"] == 0
    assert result["total_income"] == 0
    assert result["daily_average"] == 0
    assert result["categories"] == []


def test_analytics_month_changes_and_empty_data():
    rows = [
        {"date": "2026-01-03", "amount": 100, "type": "expense", "category": "Food"},
        {"date": "2026-02-03", "amount": 150, "type": "expense", "category": "Food"},
        {"date": "2026-02-04", "amount": 500, "type": "income", "category": "Other"},
    ]
    result = spending_analytics(rows)
    assert result["total_expenses"] == 250
    assert result["savings_estimate"] == 250
    assert result["comparisons"][0]["change"] == 50
    assert spending_analytics([])["monthly"] == []


def test_forecast_requires_six_real_months_and_evaluates_chronologically():
    short = [{"date": f"2026-0{month}-03", "amount": 100, "type": "expense"} for month in range(1, 5)]
    assert forecast_spending(short)["available"] is False
    history = [
        {"date": f"{year}-{month:02d}-10", "amount": 100 + (year - 2025) * 120 + month * 2, "type": "expense"}
        for year, month in [(2025, 1), (2025, 2), (2025, 3), (2025, 4), (2025, 5), (2025, 6), (2025, 7), (2025, 8)]
    ]
    result = forecast_spending(history)
    assert result["available"] is True
    assert result["next_month"] == "2025-09"
    assert len(result["evaluation"]) == 2
    assert result["mae"] >= 0


def test_anomaly_flags_iqr_outlier_and_month_increase():
    rows = [
        {"id": i, "date": f"2026-01-{i:02d}", "amount": 10, "type": "expense", "category": "Food", "description": "meal"}
        for i in range(1, 7)
    ]
    rows.append({"id": 7, "date": "2026-02-01", "amount": 1000, "type": "expense", "category": "Food", "description": "large"})
    result = detect_anomalies(rows)
    assert [row["id"] for row in result["transactions"]] == [7]
    assert result["spending_increases"][0]["increase"] == 940


def test_budget_usage_warns_near_limit_and_reports_overage():
    assert budget_usage(Decimal("100"), Decimal("79"))["status"] == "on_track"
    near_limit = budget_usage(Decimal("100"), Decimal("80"))
    assert near_limit["status"] == "warning"
    assert near_limit["remaining"] == Decimal("20")
    exceeded = budget_usage(Decimal("100"), Decimal("120"))
    assert exceeded["status"] == "exceeded"
    assert exceeded["percent_used"] == 120
