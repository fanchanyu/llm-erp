"""Pydantic schemas for Inventory API."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class PartCreate(BaseModel):
    part_no: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=200)
    unit: str = Field(..., min_length=1, max_length=10)
    spec: Optional[str] = None
    category: Optional[str] = None


class PartResponse(BaseModel):
    id: str
    part_no: str
    name: str
    unit: str
    spec: Optional[str] = None
    category: Optional[str] = None
    created_at: Optional[datetime] = None


class StockItem(BaseModel):
    part_no: str
    name: str
    spec: Optional[str] = None
    unit: str
    category: Optional[str] = None
    location: Optional[str] = None
    quantity: float
    updated_at: Optional[str] = None


class InboundRequest(BaseModel):
    part_no: str
    quantity: float = Field(..., gt=0)
    location: Optional[str] = None
    reference_no: Optional[str] = None
    notes: Optional[str] = None


class OutboundRequest(BaseModel):
    part_no: str
    quantity: float = Field(..., gt=0)
    location: Optional[str] = None
    reference_no: Optional[str] = None
    notes: Optional[str] = None


class TransactionResponse(BaseModel):
    id: str
    part_id: str
    type: str
    quantity: float
    reference_no: Optional[str] = None
    notes: Optional[str] = None
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None
