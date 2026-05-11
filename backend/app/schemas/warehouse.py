"""WMS + Supplier schemas."""

from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel, Field


# ─── Warehouse Zone ──────────────────────────────────────────────
class ZoneCreate(BaseModel):
    code: str = Field(..., max_length=20)
    name: str = Field(..., max_length=200)
    zone_type: Optional[str] = "raw"
    description: Optional[str] = None

class ZoneResponse(BaseModel):
    id: str; code: str; name: str; zone_type: str
    status: str; description: Optional[str] = None

# ─── Bin Location ────────────────────────────────────────────────
class BinCreate(BaseModel):
    zone_code: str
    code: str = Field(..., max_length=50)
    aisle: Optional[str] = None; rack: Optional[str] = None
    shelf: Optional[str] = None; bin: Optional[str] = None
    max_capacity: Optional[float] = None

class BinResponse(BaseModel):
    id: str; zone_code: Optional[str] = None; zone_name: Optional[str] = None
    code: str; aisle: Optional[str] = None; rack: Optional[str] = None
    shelf: Optional[str] = None; bin: Optional[str] = None
    max_capacity: Optional[float] = None; current_qty: float
    part_no: Optional[str] = None; status: str

# ─── Transfer ────────────────────────────────────────────────────
class TransferCreate(BaseModel):
    part_no: str; quantity: float = Field(..., gt=0)
    from_bin_code: Optional[str] = None; to_bin_code: str
    reason: Optional[str] = "transfer"; notes: Optional[str] = None

class TransferResponse(BaseModel):
    id: str; transfer_no: str; part_no: Optional[str] = None
    quantity: float; from_bin: Optional[str] = None; to_bin: Optional[str] = None
    status: str; reason: str; notes: Optional[str] = None
    created_at: Optional[datetime] = None

# ─── Pick Task ───────────────────────────────────────────────────
class PickTaskCreate(BaseModel):
    reference_type: str; reference_no: str
    part_no: str; quantity_required: float = Field(..., gt=0)
    assigned_to: Optional[str] = None; notes: Optional[str] = None

class PickTaskResponse(BaseModel):
    id: str; task_no: str; reference_type: str; reference_no: str
    part_no: Optional[str] = None; quantity_required: float; quantity_picked: float
    assigned_to: Optional[str] = None; status: str; notes: Optional[str] = None

# ─── Cycle Count ─────────────────────────────────────────────────
class CycleCountCreate(BaseModel):
    part_no: str; bin_code: Optional[str] = None; expected_qty: float
    actual_qty: float; counted_by: Optional[str] = None; notes: Optional[str] = None

class CycleCountResponse(BaseModel):
    id: str; count_no: str; part_no: Optional[str] = None
    bin_code: Optional[str] = None; expected_qty: float; actual_qty: float
    variance: float; variance_pct: Optional[float] = None; status: str
    counted_by: Optional[str] = None; notes: Optional[str] = None

# ─── Supplier Evaluation ─────────────────────────────────────────
class EvalCreate(BaseModel):
    supplier_name: str; eval_date: str
    quality_score: float = Field(..., ge=0, le=100)
    delivery_score: float = Field(..., ge=0, le=100)
    price_score: float = Field(..., ge=0, le=100)
    service_score: Optional[float] = 0
    evaluator: Optional[str] = None; notes: Optional[str] = None

class EvalResponse(BaseModel):
    id: str; supplier_name: Optional[str] = None
    eval_date: Optional[str] = None; quality_score: float; delivery_score: float
    price_score: float; total_score: float; grade: Optional[str] = None
    evaluator: Optional[str] = None; notes: Optional[str] = None

# ─── Supplier Price ──────────────────────────────────────────────
class PriceCreate(BaseModel):
    supplier_name: str; part_no: str; unit_price: float = Field(..., gt=0)
    currency: Optional[str] = "TWD"; effective_date: str
    expiry_date: Optional[str] = None; moq: Optional[float] = 1

class PriceResponse(BaseModel):
    id: str; supplier_name: Optional[str] = None
    part_no: Optional[str] = None; unit_price: float; currency: str
    effective_date: Optional[str] = None; expiry_date: Optional[str] = None
    moq: float; is_active: bool

# ─── Reorder Rule ────────────────────────────────────────────────
class ReorderRuleCreate(BaseModel):
    part_no: str; safety_stock: float = Field(..., ge=0)
    reorder_qty: float = Field(..., gt=0)
    preferred_supplier_name: Optional[str] = None
    lead_time_days: Optional[int] = 7; auto_approve: Optional[bool] = False

class ReorderRuleResponse(BaseModel):
    id: str; part_no: Optional[str] = None
    safety_stock: float; reorder_qty: float
    preferred_supplier: Optional[str] = None; lead_time_days: int
    auto_approve: bool; is_active: bool; last_triggered_at: Optional[datetime] = None

class ReorderCheckResult(BaseModel):
    part_no: str; part_name: Optional[str] = None
    current_stock: float; safety_stock: float; shortage: float
    suggested_order_qty: float; preferred_supplier: Optional[str] = None
    action: str  # none, alert, auto_order
