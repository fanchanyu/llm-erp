"""Pydantic schemas for DecisionLog and AfterActionReview APIs."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ─── DecisionLog ───────────────────────────────────────────────────

class DecisionLogCreate(BaseModel):
    decision_type: str = Field(..., pattern=r"^(rush_order|supplier_change|schedule_change|price_change|other)$")
    description: str = Field(..., min_length=1)
    department: str = Field(...)
    actor: str = Field(...)
    role: str = Field(...)
    context_data: Optional[dict] = None
    alternatives: Optional[list] = None


class DecisionLogUpdate(BaseModel):
    outcome_summary: Optional[str] = None
    status: Optional[str] = Field(None, pattern=r"^(pending|in_review|completed)$")


class DecisionLogResponse(BaseModel):
    id: int
    decision_type: str
    description: str
    department: str
    actor: str
    role: str
    context_data: Optional[dict] = None
    alternatives: Optional[list] = None
    outcome_summary: Optional[str] = None
    status: str
    created_at: Optional[datetime] = None


# ─── AfterActionReview ────────────────────────────────────────────

class AARCreate(BaseModel):
    decision_log_id: Optional[int] = None
    title: str = Field(..., min_length=1, max_length=200)
    department: str = Field(...)
    expected_result: str = Field(...)
    actual_result: str = Field(...)
    variance_analysis: Optional[str] = None
    root_cause: Optional[str] = None
    corrective_action: Optional[str] = None
    preventive_action: Optional[str] = None
    lessons_learned: Optional[str] = None
    system_rule_updates: Optional[list] = None
    status: str = Field(default="draft", pattern=r"^(draft|published|implemented)$")
    reviewer: Optional[str] = None


class AARUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    department: Optional[str] = None
    expected_result: Optional[str] = None
    actual_result: Optional[str] = None
    variance_analysis: Optional[str] = None
    root_cause: Optional[str] = None
    corrective_action: Optional[str] = None
    preventive_action: Optional[str] = None
    lessons_learned: Optional[str] = None
    system_rule_updates: Optional[list] = None
    status: Optional[str] = Field(None, pattern=r"^(draft|published|implemented)$")
    reviewer: Optional[str] = None


class AARResponse(BaseModel):
    id: int
    decision_log_id: Optional[int] = None
    title: str
    department: str
    expected_result: str
    actual_result: str
    variance_analysis: Optional[str] = None
    root_cause: Optional[str] = None
    corrective_action: Optional[str] = None
    preventive_action: Optional[str] = None
    lessons_learned: Optional[str] = None
    system_rule_updates: Optional[list] = None
    status: str
    reviewer: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
