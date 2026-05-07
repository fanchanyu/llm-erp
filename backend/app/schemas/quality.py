"""Pydantic schemas for Quality (QC) API."""

from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel, Field


# ─── Inspection Orders ────────────────────────────────────────────

class InspectionCreate(BaseModel):
    inspection_no: str = Field(..., min_length=1, max_length=50)
    po_id: Optional[str] = None
    part_id: str = Field(...)
    lot_no: Optional[str] = None
    quantity: float = Field(..., gt=0)
    inspection_date: Optional[datetime] = None
    inspected_by: Optional[str] = None


class InspectionResponse(BaseModel):
    id: str
    inspection_no: str
    po_id: Optional[str] = None
    part_id: str
    lot_no: Optional[str] = None
    quantity: float
    status: str
    inspection_date: Optional[datetime] = None
    inspected_by: Optional[str] = None
    created_at: Optional[datetime] = None


class InspectionStatusUpdate(BaseModel):
    status: str = Field(..., pattern=r"^(pending|approved|rejected|conditional)$")


# ─── Inspection Results ────────────────────────────────────────────

class InspectionResultCreate(BaseModel):
    item_no: Optional[str] = None
    description: Optional[str] = None
    spec_value: Optional[str] = None
    measured_value: Optional[str] = None
    result: str = Field(default="pass", pattern=r"^(pass|fail|conditional)$")
    notes: Optional[str] = None


class InspectionResultResponse(BaseModel):
    id: str
    inspection_id: str
    item_no: Optional[str] = None
    description: Optional[str] = None
    spec_value: Optional[str] = None
    measured_value: Optional[str] = None
    result: str
    notes: Optional[str] = None
    created_at: Optional[datetime] = None


# ─── Non-Conformances ─────────────────────────────────────────────

class NCCreate(BaseModel):
    nc_no: str = Field(..., min_length=1, max_length=50)
    inspection_id: Optional[str] = None
    part_id: str = Field(...)
    defect_code: Optional[str] = None
    description: str = Field(..., min_length=1)
    severity: str = Field(default="minor", pattern=r"^(minor|major|critical)$")
    created_by: Optional[str] = None


class NCResponse(BaseModel):
    id: str
    nc_no: str
    inspection_id: Optional[str] = None
    part_id: str
    defect_code: Optional[str] = None
    description: str
    severity: str
    status: str
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None


# ─── CAPA Records ─────────────────────────────────────────────────

class CAPACreate(BaseModel):
    root_cause: Optional[str] = None
    action: str = Field(..., min_length=1)
    responsible: Optional[str] = None
    deadline: Optional[date] = None


class CAPAResponse(BaseModel):
    id: str
    nc_id: str
    root_cause: Optional[str] = None
    action: str
    responsible: Optional[str] = None
    deadline: Optional[date] = None
    status: str
    closed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
