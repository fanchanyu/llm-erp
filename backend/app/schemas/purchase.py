"""Pydantic schemas for Purchase API."""

from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel, Field


class SupplierCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    contact: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None


class SupplierResponse(BaseModel):
    id: str
    name: str
    contact: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    score: float = 5.0


class POItemInput(BaseModel):
    part_no: str
    quantity: float = Field(..., gt=0)
    unit_price: Optional[float] = None
    expected_delivery: Optional[date] = None


class POCreate(BaseModel):
    supplier_name: str
    items: list[POItemInput] = Field(..., min_length=1)
    ordered_by: Optional[str] = None
    notes: Optional[str] = None


class POItemResponse(BaseModel):
    id: str
    part_no: str
    part_name: str
    quantity: float
    unit_price: Optional[float] = None
    expected_delivery: Optional[date] = None
    received_qty: float


class POResponse(BaseModel):
    id: str
    po_no: str
    supplier_name: str
    status: str
    items: list[POItemResponse] = []
    ordered_by: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None


class POStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(draft|sent|partial|received|cancelled)$")
