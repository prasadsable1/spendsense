import csv
import io
import json
import os
import re
from calendar import monthrange
from contextlib import asynccontextmanager
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Annotated

import pandas as pd
from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import and_, extract, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.analytics import budget_usage, detect_anomalies, forecast_spending, spending_analytics, summarize_transactions
from app.auth import auth_required, issue_token, validate_auth_settings, verify_password, verify_token
from app.config import cors_origins, validate_production_cors
from app.database import Base, get_db, get_engine
from app.models import Budget, Category, ImportHistory, Transaction
from app.schemas import BudgetInput, BudgetOutput, CategoryInput, CategoryOutput, LoginInput, TransactionInput, TransactionOutput

DEFAULT_CATEGORIES = [
    ("Food", "#f0a85c"), ("Travel", "#6db9d0"), ("Shopping", "#b28bfa"),
    ("Bills", "#7292ff"), ("Education", "#7bc9a4"), ("Healthcare", "#ee8293"),
    ("Entertainment", "#cb86da"), ("Rent", "#d9c46b"), ("Groceries", "#84bd71"),
    ("Other", "#8d9ab3"),
]
MAX_UPLOAD_BYTES = 5 * 1024 * 1024


def initialize_database() -> None:
    Base.metadata.create_all(bind=get_engine())
    from app.database import get_session_factory

    with get_session_factory()() as db:
        existing = set(db.scalars(select(Category.name)).all())
        db.add_all(Category(name=name, color=color) for name, color in DEFAULT_CATEGORIES if name not in existing)
        db.commit()


@asynccontextmanager
async def lifespan(_: FastAPI):
    validate_auth_settings()
    validate_production_cors()
    initialize_database()
    yield


app = FastAPI(
    title="SpendSense API",
    version="1.0.0",
    description="Personal expense management and intelligence.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.middleware("http")
async def require_authenticated_owner(request: Request, call_next):
    public_paths = {"/api/health", "/api/auth/status", "/api/auth/login"}
    if (
        request.url.path.startswith("/api/")
        and request.url.path not in public_paths
        and request.method != "OPTIONS"
        and auth_required()
    ):
        scheme, _, token = request.headers.get("authorization", "").partition(" ")
        secret = os.environ.get("APP_SECRET_KEY", "")
        if (
            scheme.lower() != "bearer"
            or not token
            or not verify_token(token, secret)
        ):
            return JSONResponse(
                status_code=401,
                content={"detail": "Sign in to access your SpendSense data."},
                headers={"WWW-Authenticate": "Bearer"},
            )
    return await call_next(request)


def _transaction_query(db: Session, year: int | None = None, month: int | None = None):
    query = select(Transaction).options(joinedload(Transaction.category))
    if year is not None:
        first_month = month or 1
        last_month = month or 12
        start = date(year, first_month, 1)
        end = (
            date(year + 1, 1, 1)
            if last_month == 12
            else date(year, last_month + 1, 1)
        )
        query = query.where(Transaction.date >= start, Transaction.date < end)
    elif month is not None:
        query = query.where(extract("month", Transaction.date) == month)
    return query


def _rows(db: Session) -> list[dict]:
    transactions = db.scalars(_transaction_query(db)).unique().all()
    return [
        {
            "id": tx.id, "date": tx.date, "amount": float(tx.amount), "type": tx.type,
            "description": tx.description, "merchant": tx.merchant, "category": tx.category.name,
        }
        for tx in transactions
    ]


def _require_category(db: Session, category_id: int) -> Category:
    category = db.get(Category, category_id)
    if category is None:
        raise HTTPException(422, "The selected category does not exist.")
    return category


@app.get("/api/health")
def health(db: Session = Depends(get_db)):
    db.execute(select(1))
    return {"status": "ok", "database": "connected"}


@app.get("/api/auth/status")
def authentication_status():
    return {"required": auth_required()}


@app.post("/api/auth/login")
def login(payload: LoginInput):
    if not auth_required():
        raise HTTPException(404, "Authentication is not enabled.")
    encoded_password = os.environ.get("APP_PASSWORD_HASH", "")
    if not verify_password(payload.password, encoded_password):
        raise HTTPException(
            401,
            "Incorrect password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = issue_token(os.environ["APP_SECRET_KEY"])
    return {
        "access_token": token,
        "token_type": "bearer",
    }


@app.get("/api/auth/me")
def current_user():
    return {"authenticated": True}


@app.get("/api/categories", response_model=list[CategoryOutput])
def list_categories(db: Session = Depends(get_db)):
    return db.scalars(select(Category).order_by(Category.name)).all()


@app.post("/api/categories", response_model=CategoryOutput, status_code=201)
def create_category(payload: CategoryInput, db: Session = Depends(get_db)):
    category = Category(name=payload.name.strip(), color=payload.color)
    db.add(category)
    try:
        db.commit()
        db.refresh(category)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "A category with this name already exists.") from exc
    return category


@app.delete("/api/categories/{category_id}", status_code=204)
def delete_category(category_id: int, db: Session = Depends(get_db)):
    category = db.get(Category, category_id)
    if category is None:
        raise HTTPException(404, "Category not found.")
    if db.scalar(select(func.count()).select_from(Transaction).where(Transaction.category_id == category_id)):
        raise HTTPException(409, "A category used by transactions cannot be deleted.")
    db.delete(category)
    db.commit()


@app.get("/api/transactions", response_model=list[TransactionOutput])
def list_transactions(
    search: str | None = None, year: int | None = Query(default=None, ge=2000, le=2200),
    month: int | None = Query(default=None, ge=1, le=12), category_id: int | None = None,
    type: str | None = Query(default=None, pattern="^(expense|income)$"),
    sort: str = Query(default="date", pattern="^(date|amount|description)$"),
    order: str = Query(default="desc", pattern="^(asc|desc)$"),
    limit: int = Query(default=100, ge=1, le=500), offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    query = _transaction_query(db, year, month)
    if search:
        term = f"%{search.strip()}%"
        query = query.join(Transaction.category).where(
            or_(Transaction.description.ilike(term), Transaction.merchant.ilike(term), Category.name.ilike(term))
        )
    if category_id is not None:
        query = query.where(Transaction.category_id == category_id)
    if type:
        query = query.where(Transaction.type == type)
    column = {"date": Transaction.date, "amount": Transaction.amount, "description": Transaction.description}[sort]
    query = query.order_by(column.desc() if order == "desc" else column.asc()).offset(offset).limit(limit)
    return db.scalars(query).unique().all()


@app.get("/api/transactions/count")
def count_transactions(
    search: str | None = None, category_id: int | None = None,
    type: str | None = Query(default=None, pattern="^(expense|income)$"),
    db: Session = Depends(get_db),
):
    query = select(func.count()).select_from(Transaction)
    if search:
        term = f"%{search.strip()}%"
        query = query.join(Transaction.category).where(
            or_(Transaction.description.ilike(term), Transaction.merchant.ilike(term), Category.name.ilike(term))
        )
    if category_id is not None:
        query = query.where(Transaction.category_id == category_id)
    if type:
        query = query.where(Transaction.type == type)
    return {"count": db.scalar(query)}


@app.post("/api/transactions", response_model=TransactionOutput, status_code=201)
def create_transaction(payload: TransactionInput, db: Session = Depends(get_db)):
    _require_category(db, payload.category_id)
    transaction = Transaction(**payload.model_dump())
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return db.scalar(_transaction_query(db).where(Transaction.id == transaction.id))


@app.put("/api/transactions/{transaction_id}", response_model=TransactionOutput)
def update_transaction(transaction_id: int, payload: TransactionInput, db: Session = Depends(get_db)):
    transaction = db.get(Transaction, transaction_id)
    if transaction is None:
        raise HTTPException(404, "Transaction not found.")
    _require_category(db, payload.category_id)
    for key, value in payload.model_dump().items():
        setattr(transaction, key, value)
    db.commit()
    return db.scalar(_transaction_query(db).where(Transaction.id == transaction_id))


@app.delete("/api/transactions/{transaction_id}", status_code=204)
def delete_transaction(transaction_id: int, db: Session = Depends(get_db)):
    transaction = db.get(Transaction, transaction_id)
    if transaction is None:
        raise HTTPException(404, "Transaction not found.")
    db.delete(transaction)
    db.commit()


def _period_budgets(db: Session, year: int, month: int) -> list[dict]:
    budgets = db.scalars(select(Budget).options(joinedload(Budget.category)).where(
        Budget.year == year, Budget.month == month
    )).unique().all()
    start = date(year, month, 1)
    end = date(year, month, monthrange(year, month)[1])
    result = []
    for budget in budgets:
        query = select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            Transaction.type == "expense", Transaction.date >= start, Transaction.date <= end
        )
        if budget.category_id is not None:
            query = query.where(Transaction.category_id == budget.category_id)
        spent = Decimal(str(db.scalar(query)))
        amount = Decimal(budget.amount)
        usage = budget_usage(amount, spent)
        result.append({
            "id": budget.id, "year": year, "month": month, "amount": amount,
            "category_id": budget.category_id, "category_name": budget.category.name if budget.category else None,
            **usage,
        })
    return result


@app.get("/api/budgets", response_model=list[BudgetOutput])
def list_budgets(year: int = Query(ge=2000, le=2200), month: int = Query(ge=1, le=12), db: Session = Depends(get_db)):
    return _period_budgets(db, year, month)


@app.post("/api/budgets", response_model=BudgetOutput, status_code=201)
def upsert_budget(payload: BudgetInput, db: Session = Depends(get_db)):
    if payload.category_id is not None:
        _require_category(db, payload.category_id)
    query = select(Budget).where(Budget.year == payload.year, Budget.month == payload.month)
    query = query.where(Budget.category_id == payload.category_id) if payload.category_id is not None else query.where(Budget.category_id.is_(None))
    budget = db.scalar(query)
    if budget is None:
        budget = Budget(**payload.model_dump())
        db.add(budget)
    else:
        budget.amount = payload.amount
    db.commit()
    db.refresh(budget)
    return next(row for row in _period_budgets(db, payload.year, payload.month) if row["id"] == budget.id)


@app.delete("/api/budgets/{budget_id}", status_code=204)
def delete_budget(budget_id: int, db: Session = Depends(get_db)):
    budget = db.get(Budget, budget_id)
    if budget is None:
        raise HTTPException(404, "Budget not found.")
    db.delete(budget)
    db.commit()


@app.get("/api/dashboard")
def dashboard(year: int = Query(ge=2000, le=2200), month: int = Query(ge=1, le=12), db: Session = Depends(get_db)):
    rows = _rows(db)
    stats = summarize_transactions(rows, year, month)
    budgets = _period_budgets(db, year, month)
    stats["budgets"] = budgets
    overall_budget = next((b for b in budgets if b["category_id"] is None), None)
    selected_budgets = [overall_budget] if overall_budget else [b for b in budgets if b["category_id"] is not None]
    stats["remaining_budget"] = round(sum(float(b["remaining"]) for b in selected_budgets), 2) if budgets else None
    stats["budget_usage"] = budgets
    stats["recent_transactions"] = [
        TransactionOutput.model_validate(tx).model_dump(mode="json")
        for tx in db.scalars(_transaction_query(db).order_by(Transaction.date.desc(), Transaction.id.desc()).limit(6)).unique().all()
    ]
    expenses = pd.DataFrame(rows)
    if not expenses.empty:
        expenses = expenses[expenses["type"] == "expense"].copy()
        expenses["date"] = pd.to_datetime(expenses["date"])
    trend = []
    for offset in range(5, -1, -1):
        absolute_month = year * 12 + month - 1 - offset
        trend_year, trend_month0 = divmod(absolute_month, 12)
        trend_month = trend_month0 + 1
        total = 0
        if not expenses.empty:
            match = expenses[(expenses["date"].dt.year == trend_year) & (expenses["date"].dt.month == trend_month)]
            total = float(match["amount"].sum())
        trend.append({"month": f"{trend_year}-{trend_month:02d}", "amount": round(total, 2)})
    stats["monthly_trend"] = trend
    return stats


@app.get("/api/analytics")
def analytics(db: Session = Depends(get_db)):
    return spending_analytics(_rows(db))


@app.get("/api/predictions")
def predictions(db: Session = Depends(get_db)):
    return forecast_spending(_rows(db))


@app.get("/api/anomalies")
def anomalies(db: Session = Depends(get_db)):
    return detect_anomalies(_rows(db))


def _csv_content(db: Session, year: int | None = None, month: int | None = None) -> str:
    query = _transaction_query(db, year, month).order_by(Transaction.date.desc())
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["date", "amount", "type", "category", "description", "merchant", "payment_method"])
    for tx in db.scalars(query).unique().all():
        writer.writerow([tx.date.isoformat(), tx.amount, tx.type, tx.category.name, tx.description, tx.merchant or "", tx.payment_method])
    return output.getvalue()


@app.get("/api/reports/monthly")
def monthly_report(year: int = Query(ge=2000, le=2200), month: int = Query(ge=1, le=12), db: Session = Depends(get_db)):
    rows = [r for r in _rows(db) if r["date"].year == year and r["date"].month == month]
    return {"year": year, "month": month, "summary": spending_analytics(rows),
            "categories": summarize_transactions(rows, year, month)["categories"],
            "transaction_count": len(rows)}


@app.get("/api/reports/export")
def export_report(
    year: int | None = Query(default=None, ge=2000, le=2200),
    month: int | None = Query(default=None, ge=1, le=12), db: Session = Depends(get_db),
):
    content = _csv_content(db, year, month)
    filename = f"spendsense-{year}-{month:02d}.csv" if year and month else "spendsense-transactions.csv"
    return StreamingResponse(iter([content]), media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="{filename}"'})


def _decode_csv(content: bytes) -> list[dict[str, str]]:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(400, "CSV must use UTF-8 encoding.") from exc
    try:
        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames or len(reader.fieldnames) < 2:
            raise HTTPException(400, "CSV needs a header row and transaction columns.")
        if any(not name for name in reader.fieldnames):
            raise HTTPException(400, "CSV contains an empty column name.")
        rows = list(reader)
        if not rows:
            raise HTTPException(400, "CSV contains no transaction rows.")
        if len(rows) > 10000:
            raise HTTPException(400, "CSV is limited to 10,000 transaction rows.")
        return rows
    except csv.Error as exc:
        raise HTTPException(400, "Could not parse this CSV file.") from exc


def _read_upload(upload: UploadFile) -> bytes:
    if not upload.filename or not upload.filename.lower().endswith(".csv"):
        raise HTTPException(400, "Upload a .csv file.")
    content = upload.file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "CSV files are limited to 5 MB.")
    return content


def _suggest_columns(headers: list[str]) -> dict[str, str | None]:
    normalized = {re.sub(r"[^a-z]", "", header.lower()): header for header in headers}
    aliases = {
        "date": ("date", "transactiondate", "posteddate", "valuedate"),
        "description": ("description", "details", "narrative", "memo", "transactiondescription"),
        "amount": ("amount", "transactionamount"),
        "debit": ("debit", "withdrawal", "withdrawals"),
        "credit": ("credit", "deposit", "deposits"),
        "merchant": ("merchant", "payee", "counterparty"),
        "category": ("category",),
        "type": ("type", "transactiontype", "direction", "debitcredit"),
    }
    return {key: next((normalized[candidate] for candidate in candidates if candidate in normalized), None) for key, candidates in aliases.items()}


@app.post("/api/imports/preview")
async def preview_import(file: Annotated[UploadFile, File()]):
    rows = _decode_csv(_read_upload(file))
    headers = list(rows[0].keys())
    return {"filename": re.sub(r"[^a-zA-Z0-9._-]", "_", file.filename or "transactions.csv"),
            "columns": headers, "suggested_mapping": _suggest_columns(headers), "preview": rows[:8], "row_count": len(rows)}


def _parse_import_row(row: dict[str, str], mapping: dict, category_default: int | None, db: Session) -> dict:
    date_col = mapping.get("date")
    description_col = mapping.get("description")
    amount_col = mapping.get("amount")
    debit_col, credit_col = mapping.get("debit"), mapping.get("credit")
    if not date_col or not description_col or (not amount_col and not (debit_col or credit_col)):
        raise HTTPException(422, "Map date, description, and either amount or debit/credit columns.")
    try:
        tx_date = pd.to_datetime(row.get(date_col, ""), errors="raise").date()
    except (ValueError, TypeError) as exc:
        raise HTTPException(422, f"Invalid transaction date: {row.get(date_col, '')!r}.") from exc
    category_name = (row.get(mapping.get("category"), "") or "").strip() if mapping.get("category") else ""
    category = db.scalar(select(Category).where(func.lower(Category.name) == category_name.lower())) if category_name else None
    if category is None and category_default:
        category = _require_category(db, category_default)
    if category is None:
        category = db.scalar(select(Category).where(Category.name == "Other"))
    if amount_col:
        raw_amount = (row.get(amount_col, "") or "").replace("$", "").replace(",", "").strip()
        try:
            amount = Decimal(raw_amount)
        except InvalidOperation as exc:
            raise HTTPException(422, f"Invalid transaction amount: {raw_amount!r}.") from exc
        tx_type = "expense" if amount < 0 else "expense"
        type_col = mapping.get("type")
        if type_col:
            direction = (row.get(type_col, "") or "").strip().lower()
            direction_words = set(re.findall(r"[a-z]+", direction))
            if direction_words & {"expense", "debit", "withdrawal", "purchase", "charge", "payment", "bill"}:
                tx_type = "expense"
            elif direction_words & {"income", "credit", "deposit", "refund", "salary", "interest"}:
                tx_type = "income"
        amount = abs(amount)
    else:
        debit = (row.get(debit_col, "") or "").replace("$", "").replace(",", "").strip() if debit_col else ""
        credit = (row.get(credit_col, "") or "").replace("$", "").replace(",", "").strip() if credit_col else ""
        try:
            debit_amount = abs(Decimal(debit)) if debit else Decimal("0")
            credit_amount = abs(Decimal(credit)) if credit else Decimal("0")
        except InvalidOperation as exc:
            raise HTTPException(422, "Invalid debit or credit amount.") from exc
        if debit_amount and credit_amount:
            raise HTTPException(422, "A row cannot contain both a debit and credit amount.")
        amount, tx_type = (debit_amount, "expense") if debit_amount else (credit_amount, "income")
    if amount <= 0 or amount > Decimal("9999999999.99") or amount.as_tuple().exponent < -2:
        raise HTTPException(422, "Transaction amounts must be greater than zero and at most 10 digits.")
    description = (row.get(description_col, "") or "").strip()
    if not description:
        raise HTTPException(422, "Transaction descriptions cannot be empty.")
    merchant_col = mapping.get("merchant")
    merchant = (row.get(merchant_col, "") or "").strip()[:120] if merchant_col else ""
    return {"date": tx_date, "amount": amount, "type": tx_type, "description": description[:240],
            "merchant": merchant or None, "payment_method": "Other", "category_id": category.id}


@app.post("/api/imports/confirm")
async def confirm_import(
    file: Annotated[UploadFile, File()], mapping: Annotated[str, Form()],
    category_id: Annotated[int | None, Form()] = None, db: Session = Depends(get_db),
):
    try:
        column_mapping = json.loads(mapping)
        if not isinstance(column_mapping, dict):
            raise ValueError("Mapping must be an object.")
    except (json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(422, "Column mapping must be a JSON object.") from exc
    rows = _decode_csv(_read_upload(file))
    transactions = [_parse_import_row(row, column_mapping, category_id, db) for row in rows]
    existing = db.execute(select(Transaction.date, Transaction.amount, Transaction.description, Transaction.merchant, Transaction.type)).all()
    signatures = {(r.date, Decimal(r.amount), r.description.strip().lower(), (r.merchant or "").strip().lower(), r.type) for r in existing}
    imported = duplicates = 0
    for values in transactions:
        signature = (values["date"], values["amount"], values["description"].strip().lower(),
                     (values["merchant"] or "").strip().lower(), values["type"])
        if signature in signatures:
            duplicates += 1
            continue
        signatures.add(signature)
        db.add(Transaction(**values))
        imported += 1
    history = ImportHistory(
        filename=re.sub(r"[^a-zA-Z0-9._-]", "_", file.filename or "transactions.csv")[:180],
        imported_count=imported, duplicate_count=duplicates,
    )
    db.add(history)
    db.commit()
    return {"imported": imported, "duplicates": duplicates, "skipped": duplicates, "total_rows": len(rows)}
