"""Pydantic schemas for Factory Config API."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class FactoryConfigCreate(BaseModel):
    factory_type: str = Field("MTO", pattern=r"^(MTO|MTS|ETO)$")
    name: str = Field("Default Factory", max_length=200)
    pipeline_stages: Optional[str] = None
    enabled_forms: Optional[str] = None
    cash_flow_rules: Optional[str] = None


class FactoryConfigResponse(BaseModel):
    id: int
    factory_type: str
    name: str
    pipeline_stages: Optional[str] = None
    enabled_forms: Optional[str] = None
    cash_flow_rules: Optional[str] = None
    created_at: Optional[datetime] = None
