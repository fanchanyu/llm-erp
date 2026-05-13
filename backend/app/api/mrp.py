"""MRP API — Material Requirements Planning CRUD, calculation, and item results."""

import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services import mrp_service as svc
from app.schemas.mrp import (
    MrpMasterCreate, MrpMasterUpdate, MrpMasterResponse,
    MrpMasterListResponse,
    MrpItemResponse, MrpItemListResponse,
)

router = APIRouter(prefix="/mrp", tags=["mrp"])


# ── Run MRP request body ─────────────────────────────────────

class MrpRunRequest(BaseModel):
    """MRP 運算請求 (mrp_id 取自 URL path)"""
    starting_inventory: float = Field(0, ge=0, description="期初庫存")
    max_bom_level: int = Field(3, ge=1, le=10, description="BOM 最大展開階層")


# ═══════════════════════════════════════════════════════════════════
# ─── MRP MASTER ───────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════

@router.post("/masters", response_model=MrpMasterResponse, status_code=201)
async def create_mrp_master(data: MrpMasterCreate, db: AsyncSession = Depends(get_db)):
    """Create a new MRP master plan."""
    master = await svc.create_mrp_master(
        db,
        name=data.name,
        description=data.description,
        mps_id=data.mps_id,
        created_by=data.created_by,
    )
    return MrpMasterResponse(
        id=str(master.id),
        name=master.name,
        description=master.description,
        mps_id=str(master.mps_id),
        status=master.status,
        created_by=master.created_by,
        created_at=master.created_at,
        updated_at=master.updated_at,
    )


@router.get("/masters", response_model=MrpMasterListResponse)
async def list_mrp_masters(
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List MRP masters, optionally filtered by status."""
    masters = await svc.list_mrp_masters(db, status=status or "", limit=limit)
    items = [
        MrpMasterResponse(
            id=str(m.id),
            name=m.name,
            description=m.description,
            mps_id=str(m.mps_id),
            status=m.status,
            created_by=m.created_by,
            created_at=m.created_at,
            updated_at=m.updated_at,
        )
        for m in masters
    ]
    return MrpMasterListResponse(masters=items, total=len(items))


@router.get("/masters/{mrp_id}", response_model=MrpMasterResponse)
async def get_mrp_master(mrp_id: str, db: AsyncSession = Depends(get_db)):
    """Get a single MRP master by ID."""
    master = await svc.get_mrp_master(db, master_id=mrp_id)
    if not master:
        raise HTTPException(404, "MRP master not found")
    return MrpMasterResponse(
        id=str(master.id),
        name=master.name,
        description=master.description,
        mps_id=str(master.mps_id),
        status=master.status,
        created_by=master.created_by,
        created_at=master.created_at,
        updated_at=master.updated_at,
    )


# ═══════════════════════════════════════════════════════════════════
# ─── MRP CALCULATION (RUN) ──────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════

@router.post("/masters/{mrp_id}/run", response_model=dict)
async def run_mrp_calculation(
    mrp_id: str,
    data: MrpRunRequest,
    db: AsyncSession = Depends(get_db),
):
    """Execute MRP calculation (BOM explosion → net requirements → lead time offset).

    Generates time-phased material requirements from the associated MPS
    planned orders, performs multi-level BOM explosion, calculates net
    requirements against on-hand inventory and in-transit receipts, and
    applies lead time offset for planned order release suggestions.
    """
    result = await svc.run_mrp(
        db,
        mrp_id=mrp_id,
        starting_inventory=data.starting_inventory,
        max_bom_level=data.max_bom_level,
    )
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


# ═══════════════════════════════════════════════════════════════════
# ─── MRP ITEMS (RESULTS) ─────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════

@router.get("/masters/{mrp_id}/items", response_model=MrpItemListResponse)
async def get_mrp_items(
    mrp_id: str,
    part_no: Optional[str] = Query(None),
    bom_level: Optional[int] = Query(None, ge=0, description="Filter by BOM level"),
    db: AsyncSession = Depends(get_db),
):
    """Get MRP calculation results (items) for a given master.

    Optionally filter by part_no or BOM level.
    """
    master = await svc.get_mrp_master(db, master_id=mrp_id)
    if not master:
        raise HTTPException(404, "MRP master not found")

    items = await svc.get_mrp_items(
        db,
        mrp_id=mrp_id,
        part_no=part_no or "",
        bom_level=bom_level if bom_level is not None else -1,
    )
    result_items = [
        MrpItemResponse(
            id=str(i.id),
            mrp_id=str(i.mrp_id),
            product_no=i.product_no,
            part_no=i.part_no,
            part_name=i.part_name,
            bom_level=i.bom_level,
            period_week=i.period_week,
            gross_requirement=i.gross_requirement or 0,
            scheduled_receipts=i.scheduled_receipts or 0,
            projected_balance=i.projected_balance or 0,
            net_requirement=i.net_requirement or 0,
            planned_order_qty=i.planned_order_qty or 0,
            planned_order_release=i.planned_order_release or 0,
            order_type=i.order_type,
            lead_time_days=i.lead_time_days or 0,
            source=i.source,
            exception_message=i.exception_message,
            created_at=i.created_at,
            updated_at=i.updated_at,
        )
        for i in items
    ]
    return MrpItemListResponse(items=result_items, total=len(result_items))
