"""Pydantic schemas for Contract API."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ContractCreate(BaseModel):
    contract_no: str = Field(..., min_length=1, max_length=50)
    customer_id: int = Field(...)
    type: str = Field(..., pattern=r"^(annual|framework|project|one_time)$")
    start_date: datetime = Field(...)
    end_date: Optional[datetime] = None
    pricing_json: Optional[dict] = None
    payment_terms: Optional[str] = None
    status: str = Field(default="draft", pattern=r"^(draft|active|expired|terminated)$")
    auto_renew: bool = False
    notes: Optional[str] = None


class ContractUpdate(BaseModel):
    contract_no: Optional[str] = Field(None, min_length=1, max_length=50)
    customer_id: Optional[int] = None
    type: Optional[str] = Field(None, pattern=r"^(annual|framework|project|one_time)$")
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    pricing_json: Optional[dict] = None
    payment_terms: Optional[str] = None
    status: Optional[str] = Field(None, pattern=r"^(draft|active|expired|terminated)$")
    auto_renew: Optional[bool] = None
    notes: Optional[str] = None


class ContractResponse(BaseModel):
    id: int
    contract_no: str
    customer_id: int
    type: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    pricing_json: Optional[dict] = None
    payment_terms: Optional[str] = None
    status: str
    auto_renew: bool
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ContractPricingResponse(BaseModel):
    part_no: str
    unit_price: float
    min_qty: float
    discount_pct: float
