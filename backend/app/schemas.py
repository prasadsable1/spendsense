from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TransactionInput(BaseModel):
    date: date
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    type: Literal["expense", "income"] = "expense"
    description: str = Field(min_length=1, max_length=240)
    merchant: str | None = Field(default=None, max_length=120)
    payment_method: str = Field(default="Other", max_length=40)
    category_id: int


class TransactionOutput(TransactionInput):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category: "CategoryOutput"


class CategoryInput(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    color: str = Field(default="#7186ff", pattern=r"^#[0-9a-fA-F]{6}$")


class CategoryOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    color: str


class BudgetInput(BaseModel):
    year: int = Field(ge=2000, le=2200)
    month: int = Field(ge=1, le=12)
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    category_id: int | None = None


class BudgetOutput(BaseModel):
    id: int
    year: int
    month: int
    amount: Decimal
    category_id: int | None
    category_name: str | None
    spent: Decimal
    remaining: Decimal
    percent_used: float
    status: str


class LoginInput(BaseModel):
    password: str = Field(min_length=1, max_length=1024)
