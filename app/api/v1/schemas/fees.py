from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class FeeHeadOut(BaseModel):
    id: int
    name: str
    code: str
    is_active: bool


class FeeHeadCreateIn(BaseModel):
    name: str = Field(min_length=2, max_length=64)
    code: str = Field(min_length=2, max_length=24)


class FeeCategoryCreateIn(BaseModel):
    name: str = Field(min_length=2, max_length=64)


class FeeStructureItemIn(BaseModel):
    fee_head_id: int
    amount: int = Field(ge=0, le=2_000_000)


class FeeStructureOut(BaseModel):
    id: int
    name: str | None
    session: str
    grade_name: str
    is_active: bool
    total_amount: int
    items: list[dict]


class FeeStructureCreateIn(BaseModel):
    name: str | None = Field(default=None, max_length=128)
    session: str = Field(min_length=4, max_length=16)
    grade_name: str = Field(min_length=1, max_length=32)
    items: list[FeeStructureItemIn] = Field(min_length=1)


PaymentMode = Literal["cash", "upi", "bank_transfer", "cheque"]


class FeePaymentItemIn(BaseModel):
    fee_head_id: int
    amount: int = Field(ge=0, le=2_000_000)


class FeePaymentCreateIn(BaseModel):
    student_id: int
    session: str = Field(min_length=4, max_length=16)
    amount_paid: int = Field(ge=1, le=5_000_000)
    payment_mode: PaymentMode
    payment_date: str  # ISO timestamp
    note: str | None = Field(default=None, max_length=255)
    items: list[FeePaymentItemIn] | None = None
