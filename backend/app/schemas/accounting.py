"""Pydantic schemas for Accounting API."""

from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel, Field


# ─── Account ───────────────────────────────────────────────────────

class AccountCreate(BaseModel):
    account_no: str = Field(..., min_length=1, max_length=20)
    name: str = Field(..., min_length=1, max_length=200)
    type: str = Field(..., pattern=r"^(asset|liability|equity|revenue|expense)$")
    normal_balance: str = Field(..., pattern=r"^(debit|credit)$")
    is_active: bool = True


class AccountResponse(BaseModel):
    id: str
    account_no: str
    name: str
    type: str
    normal_balance: str
    is_active: bool
    created_at: Optional[datetime] = None


# ─── Journal Entry ─────────────────────────────────────────────────

class JournalLineInput(BaseModel):
    account_no: str
    debit: float = 0
    credit: float = 0
    description: Optional[str] = None


class JournalEntryCreate(BaseModel):
    description: str = Field(..., min_length=1)
    entry_date: date
    source_type: Optional[str] = None
    source_id: Optional[str] = None
    created_by: str = Field(default="system", max_length=100)
    lines: list[JournalLineInput] = Field(..., min_length=2)


class JournalLineResponse(BaseModel):
    id: str
    account_no: str
    account_name: str
    debit: float
    credit: float
    description: Optional[str] = None


class JournalEntryResponse(BaseModel):
    id: str
    entry_no: str
    description: str
    entry_date: date
    period: str
    source_type: Optional[str] = None
    source_id: Optional[str] = None
    created_by: str
    created_at: Optional[datetime] = None
    posted: bool
    lines: list[JournalLineResponse] = []


# ─── Accounts Receivable ───────────────────────────────────────────

class ARCreate(BaseModel):
    customer_name: str = Field(..., min_length=1, max_length=200)
    invoice_no: str = Field(..., min_length=1, max_length=50)
    amount: float = Field(..., gt=0)
    due_date: date


class ARPaymentInput(BaseModel):
    paid_amount: float = Field(..., gt=0)


class ARResponse(BaseModel):
    id: str
    customer_name: str
    invoice_no: str
    amount: float
    due_date: date
    paid_amount: float
    status: str
    created_at: Optional[datetime] = None


class ARSummaryItem(BaseModel):
    customer_name: str
    invoice_no: str
    amount: float
    paid_amount: float
    due_date: date
    overdue_days: int


class ARSummaryResponse(BaseModel):
    total_overdue: int
    total_amount: float
    items: list[ARSummaryItem] = []
