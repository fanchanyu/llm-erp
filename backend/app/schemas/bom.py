"""Pydantic schemas for BOM API."""

from typing import Optional
from pydantic import BaseModel, Field


class ProductCreate(BaseModel):
    product_no: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None


class ProductResponse(BaseModel):
    id: str
    product_no: str
    name: str
    description: Optional[str] = None


class BOMItemInput(BaseModel):
    part_no: str
    quantity: float = Field(..., gt=0)
    level: int = Field(..., ge=0)
    sequence_no: Optional[int] = None


class BOMTreeItem(BaseModel):
    id: str
    product_no: str
    product_name: str
    level: int
    sequence_no: Optional[int] = None
    part_no: str
    part_name: str
    quantity: float
    unit: str


class ExplosionRequest(BaseModel):
    product_no: str
    quantity: float = Field(..., gt=0)


class ExplosionItem(BaseModel):
    level: int
    part_no: str
    name: str
    qty_per_parent: float
    required_qty: float


class ExplosionResponse(BaseModel):
    product_no: str
    demand_quantity: float
    items: list[ExplosionItem]


class ShortageItem(BaseModel):
    level: int
    part_no: str
    name: str
    required: float
    available: float
    shortage: float


class ShortageResponse(BaseModel):
    product_no: str
    demand_quantity: float
    has_shortage: bool
    shortages: list[ShortageItem]
    total_items: int
