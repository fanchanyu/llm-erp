"""Factory Config API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services import factory_service as svc
from app.schemas.factory_config import FactoryConfigCreate, FactoryConfigResponse

router = APIRouter(prefix="/factory", tags=["factory"])


@router.get("/config", response_model=FactoryConfigResponse)
async def get_factory_config(db: AsyncSession = Depends(get_db)):
    """Get the current factory configuration."""
    config = await svc.get_config(db)
    if not config:
        raise HTTPException(404, "No factory configuration found")
    return FactoryConfigResponse(
        id=config.id,
        factory_type=config.factory_type,
        name=config.name,
        pipeline_stages=config.pipeline_stages,
        enabled_forms=config.enabled_forms,
        cash_flow_rules=config.cash_flow_rules,
        created_at=config.created_at,
    )


@router.post("/config", response_model=FactoryConfigResponse, status_code=201)
async def set_factory_config(data: FactoryConfigCreate, db: AsyncSession = Depends(get_db)):
    """Set or update the factory configuration."""
    config = await svc.set_config(
        db,
        factory_type=data.factory_type,
        name=data.name,
        pipeline_stages=data.pipeline_stages,
        enabled_forms=data.enabled_forms,
        cash_flow_rules=data.cash_flow_rules,
    )
    return FactoryConfigResponse(
        id=config.id,
        factory_type=config.factory_type,
        name=config.name,
        pipeline_stages=config.pipeline_stages,
        enabled_forms=config.enabled_forms,
        cash_flow_rules=config.cash_flow_rules,
        created_at=config.created_at,
    )
