"""Pydantic schemas for Lead API."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class LeadCreate(BaseModel):
    company: str = Field(..., min_length=1, max_length=200)
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    source: str = Field("web", pattern=r"^(web|referral|cold_call|exhibition|other)$")
    score: int = Field(0, ge=0, le=100)
    assigned_to: Optional[str] = None
    notes: Optional[str] = None


class LeadUpdate(BaseModel):
    company: Optional[str] = None
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    source: Optional[str] = None
    score: Optional[int] = None
    status: Optional[str] = Field(None, pattern=r"^(new|contacted|qualified|converted|lost)$")
    assigned_to: Optional[str] = None
    notes: Optional[str] = None
    lost_reason: Optional[str] = None


class LeadResponse(BaseModel):
    id: int
    company: str
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    source: str
    score: int
    status: str
    assigned_to: Optional[str] = None
    notes: Optional[str] = None
    lost_reason: Optional[str] = None
    converted_to_customer_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
