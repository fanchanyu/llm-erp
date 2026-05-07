"""Pydantic schemas for Sales Order API."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class SalesOrderItemCreate(BaseModel):
    part_no: str = Field(..., min_length=1, max_length=50)
    quantity: float = Field(..., gt=0)
    part_name: Optional[str] = None
    unit_price: Optional[float] = 0
    delivery_date: Optional[datetime] = None


class SalesOrderCreate(BaseModel):
    customer_no: str = Field(..., min_length=1, max_length=50)
    items: list[SalesOrderItemCreate] = Field(..., min_length=1)
    notes: Optional[str] = None


class SalesOrderItemResponse(BaseModel):
    id: int
    part_no: str
    part_name: Optional[str] = None
    quantity: float
    unit_price: float
    line_total: float
    delivery_date: Optional[datetime] = None


class SalesOrderResponse(BaseModel):
    id: int
    so_no: str
    customer_name: str = ""
    status: str
    total_amount: float
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    items: list[SalesOrderItemResponse] = []
