"""Pydantic schemas for MRP (Material Requirements Planning) module.

Covers:
- MRP Master CRUD
- MRP Item CRUD
- MRP Calculation request/response (BOM explosion, net req, lead time offset)
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ── MRP Master ──

class MrpMasterCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    mps_id: str
    created_by: str = ""


class MrpMasterUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


class MrpMasterResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    mps_id: str
    status: str
    created_by: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MrpMasterListResponse(BaseModel):
    masters: list[MrpMasterResponse]
    total: int


# ── MRP Item ──

class MrpItemCreate(BaseModel):
    mrp_id: str
    product_no: str = Field(..., max_length=50)
    part_no: str = Field(..., max_length=50)
    part_name: str = ""
    bom_level: int = 0
    period_week: int = 0
    gross_requirement: float = 0
    scheduled_receipts: float = 0
    projected_balance: float = 0
    net_requirement: float = 0
    planned_order_qty: float = 0
    planned_order_release: float = 0
    order_type: str = "make"
    lead_time_days: int = 0
    source: Optional[str] = None
    exception_message: Optional[str] = None


class MrpItemUpdate(BaseModel):
    gross_requirement: Optional[float] = None
    scheduled_receipts: Optional[float] = None
    projected_balance: Optional[float] = None
    net_requirement: Optional[float] = None
    planned_order_qty: Optional[float] = None
    planned_order_release: Optional[float] = None
    exception_message: Optional[str] = None


class MrpItemResponse(BaseModel):
    id: str
    mrp_id: str
    product_no: str
    part_no: str
    part_name: str
    bom_level: int
    period_week: int
    gross_requirement: float
    scheduled_receipts: float
    projected_balance: float
    net_requirement: float
    planned_order_qty: float
    planned_order_release: float
    order_type: str
    lead_time_days: int
    source: Optional[str] = None
    exception_message: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MrpItemListResponse(BaseModel):
    items: list[MrpItemResponse]
    total: int


# ── MRP Calculation Request / Response ──

class MrpCalculateRequest(BaseModel):
    """MRP 運算請求參數"""
    mrp_id: str
    starting_inventory: float = Field(..., ge=0, description="期初庫存 (PAB 起算基礎)")
    max_bom_level: int = Field(3, ge=1, le=10, description="BOM 最大展開階層")


class MrpExplosionItem(BaseModel):
    """BOM 展開結果 — 單一料件的需求明細"""
    level: int
    product_no: str
    part_no: str
    part_name: str
    quantity: float
    unit: str = "pcs"
    order_type: str = "make"
    lead_time_days: int = 0


class MrpExplosionResponse(BaseModel):
    """BOM 展開結果回應"""
    product_no: str
    demand_quantity: float
    items: list[MrpExplosionItem]


class MrpNetRequirementItem(BaseModel):
    """淨需求計算結果 — 單一料件的供需平衡"""
    part_no: str
    part_name: str
    gross_requirement: float
    on_hand_qty: float
    allocated_qty: float
    scheduled_receipts: float
    available_qty: float
    net_requirement: float
    planned_order_qty: float
    order_type: str
    lead_time_days: int
    exception_message: Optional[str] = None


class MrpNetRequirementResponse(BaseModel):
    """淨需求計算結果回應"""
    product_no: str
    items: list[MrpNetRequirementItem]


class MrpPeriodResult(BaseModel):
    """單一時段的 MRP 計算結果"""
    period_week: int
    part_no: str
    part_name: str
    bom_level: int
    gross_requirement: float
    scheduled_receipts: float
    projected_balance: float
    net_requirement: float
    planned_order_qty: float
    planned_order_release: float
    order_type: str
    lead_time_days: int
    exception_message: Optional[str] = None


class MrpCalculationResult(BaseModel):
    """完整 MRP 運算結果"""
    mrp_id: str
    mrp_name: str
    mps_id: str
    total_items: int
    total_make_orders: int
    total_buy_orders: int
    periods: list[MrpPeriodResult]


class MrpCalculationSummary(BaseModel):
    """MRP 運算摘要"""
    mrp_id: str
    mrp_name: str
    total_periods: int
    total_items: int
    total_make_orders: int
    total_buy_orders: int
    total_net_requirements: int
    has_exceptions: bool
    exception_count: int
