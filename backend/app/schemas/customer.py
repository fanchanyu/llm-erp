"""Pydantic schemas for Customer Master API."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class CustomerCreate(BaseModel):
    customer_no: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=200)
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    credit_limit: Optional[float] = 0
    level: Optional[str] = "C"
    notes: Optional[str] = None


class CustomerResponse(BaseModel):
    id: int
    customer_no: str
    name: str
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    credit_limit: float
    level: str
    notes: Optional[str] = None
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
