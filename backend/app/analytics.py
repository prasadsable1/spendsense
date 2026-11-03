from datetime import date
from decimal import Decimal

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression


def money(value: float | int) -> float:
    return round(float(value), 2)


def budget_usage(amount: Decimal, spent: Decimal) -> dict:
    percent = float(spent / amount * 100) if amount else 0
    return {
        "spent": spent,
        "remaining": amount - spent,
        "percent_used": round(percent, 2),
        "status": "exceeded" if percent >= 100 else "warning" if percent >= 80 else "on_track",
    }


def summarize_transactions(rows: list[dict], year: int, month: int) -> dict:
    frame = pd.DataFrame(rows)
    if frame.empty:
        frame = pd.DataFrame(columns=["date", "amount", "type", "category"])
    frame["date"] = pd.to_datetime(frame["date"])
    frame["amount"] = pd.to_numeric(frame["amount"])

    expenses = frame[frame["type"] == "expense"].copy()
    incomes = frame[frame["type"] == "income"].copy()
    period = expenses[(expenses["date"].dt.year == year) & (expenses["date"].dt.month == month)]
    total_expenses = float(period["amount"].sum())
    total_income = float(
        incomes[(incomes["date"].dt.year == year) & (incomes["date"].dt.month == month)]["amount"].sum()
    )
    days_in_month = pd.Period(f"{year}-{month:02d}").days_in_month
    category_rows = (
        period.groupby("category", as_index=False)["amount"].sum().sort_values("amount", ascending=False)
    )
    daily = period.groupby(period["date"].dt.day)["amount"].sum()
    today = date.today()
    days_elapsed = min(today.day, days_in_month) if (today.year, today.month) == (year, month) else days_in_month
    budget_rows = []
    return {
        "year": year,
        "month": month,
        "total_expenses": money(total_expenses),
        "total_income": money(total_income),
        "savings_estimate": money(total_income - total_expenses),
        "daily_average": money(total_expenses / days_elapsed) if days_elapsed else 0,
        "median_transaction": money(period["amount"].median()) if not period.empty else 0,
        "highest_transaction": money(period["amount"].max()) if not period.empty else 0,
        "lowest_transaction": money(period["amount"].min()) if not period.empty else 0,
        "highest_category": (
            {"name": str(category_rows.iloc[0]["category"]), "amount": money(category_rows.iloc[0]["amount"])}
            if not category_rows.empty
            else None
        ),
        "categories": [
            {"name": str(row["category"]), "amount": money(row["amount"])}
            for _, row in category_rows.iterrows()
        ],
        "daily": [{"day": int(day), "amount": money(amount)} for day, amount in daily.items()],
        "budget_rows": budget_rows,
        "days_in_month": days_in_month,
    }


def spending_analytics(rows: list[dict]) -> dict:
    frame = pd.DataFrame(rows)
    if frame.empty:
        frame = pd.DataFrame(columns=["date", "amount", "type", "category"])
    else:
        frame["date"] = pd.to_datetime(frame["date"])
        frame["amount"] = pd.to_numeric(frame["amount"])
    expenses = frame[frame["type"] == "expense"].copy()
    monthly = (
        expenses.groupby(expenses["date"].dt.to_period("M"))["amount"].sum().sort_index()
        if not expenses.empty
        else pd.Series(dtype=float)
    )
    category_totals = expenses.groupby("category")["amount"].sum().sort_values(ascending=False)
    weekly = (
        expenses.groupby(expenses["date"].dt.to_period("W-SUN"))["amount"].sum()
        if not expenses.empty
        else pd.Series(dtype=float)
    )
    income_total = float(frame[frame["type"] == "income"]["amount"].sum()) if not frame.empty else 0
    expense_total = float(expenses["amount"].sum()) if not expenses.empty else 0
    month_rows = [{"month": str(key), "amount": money(value)} for key, value in monthly.items()]
    comparisons = []
    for index in range(1, len(month_rows)):
        previous, current = month_rows[index - 1], month_rows[index]
        previous_amount = previous["amount"]
        comparisons.append({
            "month": current["month"],
            "previous_month": previous["month"],
            "amount": current["amount"],
            "previous_amount": previous_amount,
            "change": money(current["amount"] - previous_amount),
            "change_percent": money((current["amount"] - previous_amount) / previous_amount * 100)
            if previous_amount
            else None,
        })
    return {
        "total_expenses": money(expense_total),
        "total_income": money(income_total),
        "savings_estimate": money(income_total - expense_total),
        "median_transaction": money(expenses["amount"].median()) if not expenses.empty else 0,
        "highest_transaction": money(expenses["amount"].max()) if not expenses.empty else 0,
        "lowest_transaction": money(expenses["amount"].min()) if not expenses.empty else 0,
        "average_daily_spending": money(expense_total / expenses["date"].dt.date.nunique())
        if not expenses.empty
        else 0,
        "categories": [{"category": name, "amount": money(value)} for name, value in category_totals.items()],
        "monthly": month_rows,
        "weekly": [{"week": str(key), "amount": money(value)} for key, value in weekly.items()],
        "income_vs_expenses": [
            {"type": "Income", "amount": money(income_total)},
            {"type": "Expenses", "amount": money(expense_total)},
        ],
        "comparisons": comparisons,
    }


def forecast_spending(rows: list[dict]) -> dict:
    frame = pd.DataFrame(rows)
    if frame.empty:
        return {"available": False, "reason": "Add expense transactions across at least 6 different months to build a forecast."}
    frame = frame[frame["type"] == "expense"].copy()
    if frame.empty:
        return {"available": False, "reason": "No expense history is available to forecast."}
    frame["date"] = pd.to_datetime(frame["date"])
    frame["amount"] = pd.to_numeric(frame["amount"])
    monthly = frame.groupby(frame["date"].dt.to_period("M"))["amount"].sum().sort_index()
    if len(monthly) < 6:
        return {
            "available": False,
            "reason": f"At least 6 distinct months of expense history are required; {len(monthly)} month(s) found.",
            "historical": [{"month": str(key), "actual": money(value)} for key, value in monthly.items()],
        }

    # A chronological holdout prevents future months from leaking into model evaluation.
    values = monthly.to_numpy(dtype=float)
    month_indexes = np.array([period.ordinal for period in monthly.index], dtype=float)
    indexes = (month_indexes - month_indexes[0]).reshape(-1, 1)
    holdout = min(3, max(2, len(values) // 4))
    split = len(values) - holdout
    evaluation_model = LinearRegression().fit(indexes[:split], values[:split])
    predictions = evaluation_model.predict(indexes[split:])
    actuals = values[split:]
    mae = float(np.mean(np.abs(actuals - predictions)))
    r_squared = (
        float(evaluation_model.score(indexes[split:], actuals))
        if len(actuals) >= 2 and np.var(actuals) > 0
        else None
    )
    model = LinearRegression().fit(indexes, values)
    predicted = max(0, float(model.predict(np.array([[indexes[-1, 0] + 1]]))[0]))
    next_month = (monthly.index[-1] + 1).strftime("%Y-%m")
    evaluation = [
        {"month": str(monthly.index[split + i]), "actual": money(actual), "predicted": money(predictions[i])}
        for i, actual in enumerate(actuals)
    ]
    return {
        "available": True,
        "next_month": next_month,
        "predicted_spending": money(predicted),
        "historical": [{"month": str(key), "actual": money(value)} for key, value in monthly.items()],
        "evaluation": evaluation,
        "mae": money(mae),
        "r_squared": money(r_squared) if r_squared is not None else None,
        "explanation": f"Linear regression on {len(values)} consecutive monthly totals; evaluation uses the last {holdout} month(s) held out from training.",
    }


def detect_anomalies(rows: list[dict]) -> dict:
    frame = pd.DataFrame(rows)
    if frame.empty:
        return {"transactions": [], "spending_increases": []}
    frame = frame[frame["type"] == "expense"].copy()
    if frame.empty:
        return {"transactions": [], "spending_increases": []}
    frame["amount"] = pd.to_numeric(frame["amount"])
    flagged = []
    for category, group in frame.groupby("category"):
        amounts = group["amount"]
        lower = float(amounts.quantile(0.25))
        upper = float(amounts.quantile(0.75))
        iqr = upper - lower
        threshold = upper + 1.5 * iqr
        if len(group) < 5:
            all_amounts = frame["amount"]
            overall_upper = float(all_amounts.quantile(0.75))
            overall_iqr = overall_upper - float(all_amounts.quantile(0.25))
            threshold = overall_upper + 1.5 * overall_iqr
            reason = "Amount is above the overall IQR range; category history is limited."
        else:
            reason = f"Amount is above the {category} category's IQR outlier threshold."
        for row in group[group["amount"] > threshold].to_dict("records"):
            flagged.append({
                "id": int(row["id"]),
                "date": str(row["date"]),
                "description": row["description"],
                "category": category,
                "amount": money(row["amount"]),
                "reason": reason,
            })

    monthly = frame.groupby(pd.to_datetime(frame["date"]).dt.to_period("M")).agg(
        amount=("amount", "sum"), category=("category", "first")
    ).sort_index()
    increases = []
    if len(monthly) >= 2 and monthly.index[-1].ordinal - monthly.index[-2].ordinal == 1:
        latest, previous = monthly.iloc[-1], monthly.iloc[-2]
        if float(latest["amount"]) > float(previous["amount"]):
            increases.append({
                "month": str(monthly.index[-1]),
                "previous_month": str(monthly.index[-2]),
                "amount": money(latest["amount"]),
                "previous_amount": money(previous["amount"]),
                "increase": money(latest["amount"] - previous["amount"]),
                "reason": "Total expenses increased compared with the previous month.",
            })
    return {"transactions": flagged, "spending_increases": increases}
