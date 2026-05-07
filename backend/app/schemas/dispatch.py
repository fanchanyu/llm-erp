"""Pydantic schemas for dispatch / production order module."""

from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel


# ── WorkCenter ──

class WorkCenterCreate(BaseModel):
    name: str
    description: str = ""
    capacity_hours: float = 8.0
    efficiency: float = 1.0
    location: str = ""
    alternate_group: str = ""


class WorkCenterUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    capacity_hours: Optional[float] = None
    efficiency: Optional[float] = None
    status: Optional[str] = None
    location: Optional[str] = None
    alternate_group: Optional[str] = None


class WorkCenterResponse(BaseModel):
    id: str
    name: str
    description: str
    status: str
    capacity_hours: float
    efficiency: float
    location: str
    alternate_group: str
    created_at: datetime

    class Config:
        from_attributes = True


# ── ProductionOrder ──

class ProductionOrderCreate(BaseModel):
    product_no: str
    product_name: str = ""
    quantity: float
    due_date: date
    priority: int = 3
    notes: str = ""
    created_by: str = ""


class ProductionOrderUpdate(BaseModel):
    status: Optional[str] = None
    priority: Optional[int] = None
    due_date: Optional[date] = None
    notes: Optional[str] = None


class ProductionOrderResponse(BaseModel):
    id: str
    order_no: str
    product_no: str
    product_name: str
    quantity: float
    due_date: date
    priority: int
    status: str
    notes: str
    created_by: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ── Operation ──

class OperationCreate(BaseModel):
    work_center_name: str
    sequence_no: int
    name: str = ""
    setup_time_min: float = 0
    cycle_time_min: float = 0


class OperationResponse(BaseModel):
    id: str
    order_id: str
    work_center_id: str
    work_center_name: str = ""
    sequence_no: int
    name: str
    setup_time_min: float
    cycle_time_min: float
    total_time_min: float
    status: str
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None
    actual_start: Optional[datetime] = None
    actual_end: Optional[datetime] = None
    delay_minutes: float

    class Config:
        from_attributes = True


class OrderWithOperationsResponse(ProductionOrderResponse):
    operations: list[OperationResponse] = []


# ── Dispatch ──

class DispatchRequest(BaseModel):
    order_no: str
    dispatched_by: str = "system"
    notes: str = ""


class DispatchResponse(BaseModel):
    order_no: str
    status: str
    operations_dispatched: int
    notes: str
    schedule: list[dict] = []


# ── Reschedule ──

class RescheduleRequest(BaseModel):
    strategy: str = "right_shift"          # right_shift / route_change / expedite
    work_center_name: Optional[str] = None  # for route_change: find alternative
    order_no: Optional[str] = None          # for expedite: the urgent order
    reason: str = ""


class DispatchLogResponse(BaseModel):
    id: str
    order_no: str = ""
    work_center_name: str = ""
    action: str
    dispatched_by: str
    notes: str
    created_at: datetime

    class Config:
        from_attributes = True
