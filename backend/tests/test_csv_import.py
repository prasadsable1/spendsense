import pytest
from fastapi import HTTPException

from app.main import _decode_csv, _parse_import_row, _suggest_columns


class CategoryStub:
    id = 10
    name = "Other"


class SessionStub:
    def scalar(self, _query):
        return CategoryStub()


def test_suggest_columns_handles_debit_and_credit_without_guessing_an_amount_column():
    result = _suggest_columns(["Transaction Date", "Details", "Debit", "Credit", "Merchant"])
    assert result["date"] == "Transaction Date"
    assert result["description"] == "Details"
    assert result["amount"] is None
    assert result["debit"] == "Debit"
    assert result["credit"] == "Credit"


def test_csv_amounts_default_to_expense_and_respect_explicit_income_type():
    db = SessionStub()
    row = {"Date": "2026-03-01", "Description": "Market", "Amount": "42.50", "Direction": "income"}
    values = _parse_import_row(
        row,
        {"date": "Date", "description": "Description", "amount": "Amount", "type": "Direction"},
        None,
        db,
    )
    assert values["amount"] == 42.50
    assert values["type"] == "income"

    row["Direction"] = "expense"
    values = _parse_import_row(
        row,
        {"date": "Date", "description": "Description", "amount": "Amount", "type": "Direction"},
        None,
        db,
    )
    assert values["type"] == "expense"


def test_csv_rejects_bad_encoding_and_header_only_files():
    with pytest.raises(HTTPException) as bad_encoding:
        _decode_csv(b"\xff")
    assert bad_encoding.value.status_code == 400

    with pytest.raises(HTTPException) as empty:
        _decode_csv(b"date,amount\n")
    assert empty.value.status_code == 400
