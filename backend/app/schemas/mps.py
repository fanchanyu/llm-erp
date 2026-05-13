"""Pydantic schemas for MPS (Master Production Schedule) module.

Covers:
- MPS Master CRUD
- MPS Entry CRUD
- MPS Calculation request/response (time-phased PAB & ATP)
- Time Fence management
"""

from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel, Field


# ── MPS Master ──

class MpsMasterCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    start_week: date
    end_week: date
    lot_sizing_rule: str = "lot_for_lot"
    fixed_lot_qty: Optional[float] = None
    safety_stock: float = 0
    created_by: str = ""


class MpsMasterUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    lot_sizing_rule: Optional[str] = None
    fixed_lot_qty: Optional[float] = None
    safety_stock: Optional[float] = None


class MpsMasterResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    start_week: date
    end_week: date
    status: str
    lot_sizing_rule: str
    fixed_lot_qty: Optional[float] = None
    safety_stock: float
    created_by: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ── MPS Entry ──

class MpsEntryCreate(BaseModel):
    mps_id: str
    product_no: str = Field(..., max_length=50)
    product_name: str = ""
    period_week: date
    week_number: Optional[int] = None
    forecast_qty: float = 0
    customer_orders_qty: float = 0
    scheduled_receipts: float = 0


class MpsEntryUpdate(BaseModel):
    forecast_qty: Optional[float] = None
    customer_orders_qty: Optional[float] = None
    scheduled_receipts: Optional[float] = None
    status: Optional[str] = None


class MpsEntryResponse(BaseModel):
    id: str
    mps_id: str
    product_no: str
    product_name: str
    period_week: date
    week_number: Optional[int] = None
    forecast_qty: float
    customer_orders_qty: float
    gross_requirement: float
    scheduled_receipts: float
    projected_balance: float
    planned_order_qty: float
    planned_order_release: Optional[date] = None
    available_to_promise: float
    time_fence_type: Optional[str] = None
    status: str
    exception_message: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MpsEntryListResponse(BaseModel):
    entries: list[MpsEntryResponse]
    total: int


# ── Time Fence ──

class TimeFenceCreate(BaseModel):
    mps_id: str
    fence_type: str  # demand_time_fence / planning_time_fence
    fence_week: date
    description: Optional[str] = None


class TimeFenceResponse(BaseModel):
    id: str
    mps_id: str
    fence_type: str
    fence_week: date
    description: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ── MPS Calculation Request / Response ──

class MpsCalculateRequest(BaseModel):
    """MPS 時段化展算請求參數

    對指定的 MPS Master 執行完整的 time-phased MPS 運算。
    """
    mps_id: str
    starting_inventory: float = Field(..., ge=0, description="期初庫存 (PAB 起算基礎)")
    forecast_consume: bool = True  # True = 預測耗用邏輯 (FAS); False = max(fcst, orders)
    include_existing_orders: bool = True  # 是否納入已確認工單/採購單
    recalculate_atp: bool = True


class MpsCalculateResponse(BaseModel):
    """MPS 計算結果

    包含每個時段的:
    - 時段化展算 (Forecast, Orders, GrossReq, SR, PAB, Planned Orders)
    - 可供約量 (ATP)
    - 時間柵欄資訊
    - 例外訊息
    """
    mps_id: str
    mps_name: str
    product_no: str
    product_name: str
    starting_inventory: float
    total_forecast: float
    total_customer_orders: float
    total_planned_orders: float
    periods: list["MpsPeriodResult"]
    summary: "MpsCalculationSummary"


class MpsPeriodResult(BaseModel):
    """單一時段的 MPS 計算結果"""
    period_week: date
    week_number: Optional[int] = None
    forecast_qty: float
    customer_orders_qty: float
    gross_requirement: float
    scheduled_receipts: float
    projected_balance: float
    planned_order_qty: float
    planned_order_release: Optional[date] = None
    available_to_promise: float
    time_fence_type: Optional[str] = None
    exception_message: Optional[str] = None


class MpsCalculationSummary(BaseModel):
    """MPS 計算摘要"""
    total_periods: int
    periods_with_exceptions: int
    periods_below_safety_stock: int
    periods_within_dtf: int
    final_projected_balance: float
    has_exceptions: bool
    lot_sizing_rule: str


# ── Planned Orders ──

class PlannedOrderCreate(BaseModel):
    """將 MPS 計畫訂單轉為正式工單的請求"""
    mps_id: str
    product_no: str
    period_week: date
    quantity: float = Field(..., gt=0)


class PlannedOrderResponse(BaseModel):
    mps_id: str
    product_no: str
    period_week: date
    quantity: float
    converted_to_work_order: bool
    work_order_no: Optional[str] = None
    message: str
