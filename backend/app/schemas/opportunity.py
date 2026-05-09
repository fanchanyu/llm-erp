"""Pydantic schemas for Opportunity API."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class OpportunityCreate(BaseModel):
    lead_id: Optional[int] = None
    customer_id: int = Field(..., gt=0)
    name: str = Field(..., min_length=1, max_length=200)
    amount: float = Field(0, ge=0)
    probability: int = Field(50, ge=0, le=100)
    stage: str = Field("qualification", pattern=r"^(qualification|needs_analysis|proposal|negotiation|closed_won|closed_lost)$")
    expected_close_date: Optional[datetime] = None
    notes: Optional[str] = None


class OpportunityUpdate(BaseModel):
    name: Optional[str] = None
    amount: Optional[float] = None
    probability: Optional[int] = None
    expected_close_date: Optional[datetime] = None
    notes: Optional[str] = None


class OpportunityStageUpdate(BaseModel):
    stage: str = Field(..., pattern=r"^(qualification|needs_analysis|proposal|negotiation|closed_won|closed_lost)$")
    win_reason: Optional[str] = None
    lost_reason: Optional[str] = None


class OpportunityResponse(BaseModel):
    id: int
    lead_id: Optional[int] = None
    customer_id: int
    name: str
    amount: float
    probability: int
    stage: str
    expected_close_date: Optional[datetime] = None
    win_reason: Optional[str] = None
    lost_reason: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
