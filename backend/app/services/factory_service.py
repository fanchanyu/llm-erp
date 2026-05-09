"""Factory Config Service — factory configuration CRUD."""

from __future__ import annotations
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.factory_config import FactoryConfig


async def get_config(db: AsyncSession) -> Optional[FactoryConfig]:
    """Get the current factory configuration (returns the first/only record)."""
    result = await db.execute(select(FactoryConfig).limit(1))
    return result.scalar_one_or_none()


async def set_config(
    db: AsyncSession,
    factory_type: str = "MTO",
    name: str = "Default Factory",
    pipeline_stages: Optional[str] = None,
    enabled_forms: Optional[str] = None,
    cash_flow_rules: Optional[str] = None,
) -> FactoryConfig:
    """Set or update the factory configuration (upsert logic)."""
    config = await get_config(db)
    if config:
        config.factory_type = factory_type
        config.name = name
        config.pipeline_stages = pipeline_stages
        config.enabled_forms = enabled_forms
        config.cash_flow_rules = cash_flow_rules
    else:
        config = FactoryConfig(
            factory_type=factory_type,
            name=name,
            pipeline_stages=pipeline_stages,
            enabled_forms=enabled_forms,
            cash_flow_rules=cash_flow_rules,
        )
        db.add(config)
    await db.flush()
    return config
