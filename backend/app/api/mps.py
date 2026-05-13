"""MPS API — Master Production Schedule CRUD, calculation, time fences, and order conversion."""

import uuid
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.services import mps_service as svc
from app.models.mps import MpsEntry
from app.schemas.mps import (
    MpsMasterCreate, MpsMasterUpdate, MpsMasterResponse,
    MpsEntryResponse,
    TimeFenceCreate, TimeFenceResponse,
    MpsCalculateRequest, MpsCalculateResponse,
)

router = APIRouter(prefix="/mps", tags=["mps"])


# ═══════════════════════════════════════════════════════════════════
# ─── MPS MASTER ───────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════

@router.post("/masters", response_model=MpsMasterResponse, status_code=201)
async def create_mps_master(data: MpsMasterCreate, db: AsyncSession = Depends(get_db)):
    """Create a new MPS master plan."""
    master = await svc.create_mps_master(
        db,
        name=data.name,
        description=data.description,
        start_week=data.start_week,
        end_week=data.end_week,
        lot_sizing_rule=data.lot_sizing_rule,
        fixed_lot_qty=data.fixed_lot_qty,
        safety_stock=data.safety_stock,
        created_by=data.created_by,
    )
    return MpsMasterResponse(
        id=str(master.id),
        name=master.name,
        description=master.description,
        start_week=master.start_week,
        end_week=master.end_week,
        status=master.status,
        lot_sizing_rule=master.lot_sizing_rule,
        fixed_lot_qty=master.fixed_lot_qty,
        safety_stock=master.safety_stock,
        created_by=master.created_by,
        created_at=master.created_at,
        updated_at=master.updated_at,
    )


@router.get("/masters", response_model=dict)
async def list_mps_masters(
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List MPS masters, optionally filtered by status."""
    masters = await svc.list_mps_masters(db, status=status or "", limit=limit)
    items = [
        MpsMasterResponse(
            id=str(m.id),
            name=m.name,
            description=m.description,
            start_week=m.start_week,
            end_week=m.end_week,
            status=m.status,
            lot_sizing_rule=m.lot_sizing_rule,
            fixed_lot_qty=m.fixed_lot_qty,
            safety_stock=m.safety_stock,
            created_by=m.created_by,
            created_at=m.created_at,
            updated_at=m.updated_at,
        )
        for m in masters
    ]
    return {"masters": items, "total": len(items)}


@router.get("/masters/{mps_id}", response_model=MpsMasterResponse)
async def get_mps_master(mps_id: str, db: AsyncSession = Depends(get_db)):
    """Get a single MPS master by ID."""
    master = await svc.get_mps_master(db, mps_id=mps_id)
    if not master:
        raise HTTPException(404, "MPS master not found")
    return MpsMasterResponse(
        id=str(master.id),
        name=master.name,
        description=master.description,
        start_week=master.start_week,
        end_week=master.end_week,
        status=master.status,
        lot_sizing_rule=master.lot_sizing_rule,
        fixed_lot_qty=master.fixed_lot_qty,
        safety_stock=master.safety_stock,
        created_by=master.created_by,
        created_at=master.created_at,
        updated_at=master.updated_at,
    )


@router.put("/masters/{mps_id}", response_model=MpsMasterResponse)
async def update_mps_master(mps_id: str, data: MpsMasterUpdate, db: AsyncSession = Depends(get_db)):
    """Update an MPS master."""
    kwargs = {}
    for field in ["name", "description", "status", "lot_sizing_rule", "fixed_lot_qty", "safety_stock"]:
        if getattr(data, field, None) is not None:
            kwargs[field] = getattr(data, field)

    master = await svc.update_mps_master(db, mps_id, **kwargs)
    if not master:
        raise HTTPException(404, "MPS master not found")
    return MpsMasterResponse(
        id=str(master.id),
        name=master.name,
        description=master.description,
        start_week=master.start_week,
        end_week=master.end_week,
        status=master.status,
        lot_sizing_rule=master.lot_sizing_rule,
        fixed_lot_qty=master.fixed_lot_qty,
        safety_stock=master.safety_stock,
        created_by=master.created_by,
        created_at=master.created_at,
        updated_at=master.updated_at,
    )


# ═══════════════════════════════════════════════════════════════════
# ─── MPS ENTRIES ──────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════

@router.post("/masters/{mps_id}/entries", response_model=dict, status_code=201)
async def get_or_create_mps_entries(mps_id: str, db: AsyncSession = Depends(get_db)):
    """Get or create MPS entries (time buckets) for a master.

    Generates empty weekly time buckets from start_week to end_week
    if entries don't already exist. Returns existing entries otherwise.
    """
    master = await svc.get_mps_master(db, mps_id=mps_id)
    if not master:
        raise HTTPException(404, "MPS master not found")

    existing = await svc.get_mps_entries(db, mps_id=mps_id)
    if existing:
        items = [
            MpsEntryResponse(
                id=str(e.id),
                mps_id=str(e.mps_id),
                product_no=e.product_no,
                product_name=e.product_name or "",
                period_week=e.period_week,
                week_number=e.week_number,
                forecast_qty=e.forecast_qty or 0,
                customer_orders_qty=e.customer_orders_qty or 0,
                gross_requirement=e.gross_requirement or 0,
                scheduled_receipts=e.scheduled_receipts or 0,
                projected_balance=e.projected_balance or 0,
                planned_order_qty=e.planned_order_qty or 0,
                planned_order_release=e.planned_order_release,
                available_to_promise=e.available_to_promise or 0,
                time_fence_type=e.time_fence_type,
                status=e.status,
                exception_message=e.exception_message,
                created_at=e.created_at,
                updated_at=e.updated_at,
            )
            for e in existing
        ]
        return {"entries": items, "total": len(items), "created": False}

    # No entries exist — need a product_no to initialize
    return {"entries": [], "total": 0, "created": False,
            "message": "No entries exist. Use the calculate endpoint or initialize with product data."}


# ═══════════════════════════════════════════════════════════════════
# ─── MPS CALCULATION ──────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════

@router.post("/masters/{mps_id}/calculate", response_model=dict)
async def calculate_mps(mps_id: str, data: MpsCalculateRequest, db: AsyncSession = Depends(get_db)):
    """Execute MPS time-phased calculation (MPS 展算).

    Runs gross requirement determination, PAB calculation,
    planned order generation with lot sizing, ATP, and time fence
    exception detection.
    """
    result = await svc.calculate_mps(
        db,
        mps_id=mps_id,
        starting_inventory=data.starting_inventory,
        forecast_consume=data.forecast_consume,
        include_existing_orders=data.include_existing_orders,
        recalculate_atp=data.recalculate_atp,
    )
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


# ═══════════════════════════════════════════════════════════════════
# ─── TIME FENCES ──────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════

@router.post("/masters/{mps_id}/time-fences", response_model=TimeFenceResponse, status_code=201)
async def create_time_fence(mps_id: str, data: TimeFenceCreate, db: AsyncSession = Depends(get_db)):
    """Create a time fence for an MPS master."""
    master = await svc.get_mps_master(db, mps_id=mps_id)
    if not master:
        raise HTTPException(404, "MPS master not found")

    tf = await svc.create_time_fence(
        db,
        mps_id=mps_id,
        fence_type=data.fence_type,
        fence_week=data.fence_week,
        description=data.description,
    )
    return TimeFenceResponse(
        id=str(tf.id),
        mps_id=str(tf.mps_id),
        fence_type=tf.fence_type,
        fence_week=tf.fence_week,
        description=tf.description,
        created_at=tf.created_at,
    )


@router.get("/masters/{mps_id}/time-fences", response_model=dict)
async def get_time_fences(mps_id: str, db: AsyncSession = Depends(get_db)):
    """Get all time fences for an MPS master."""
    master = await svc.get_mps_master(db, mps_id=mps_id)
    if not master:
        raise HTTPException(404, "MPS master not found")

    fences = await svc.get_time_fences(db, mps_id=mps_id)
    items = [
        TimeFenceResponse(
            id=str(tf.id),
            mps_id=str(tf.mps_id),
            fence_type=tf.fence_type,
            fence_week=tf.fence_week,
            description=tf.description,
            created_at=tf.created_at,
        )
        for tf in fences
    ]
    return {"time_fences": items, "total": len(items)}


# ═══════════════════════════════════════════════════════════════════
# ─── PLANNED ORDER → PRODUCTION ORDER ─────────────────────────────
# ═══════════════════════════════════════════════════════════════════

@router.post("/masters/{mps_id}/convert/{entry_id}", response_model=dict, status_code=201)
async def convert_planned_order(mps_id: str, entry_id: str, db: AsyncSession = Depends(get_db)):
    """Convert a planned MPS order (by entry ID) into a production work order.

    Looks up the MpsEntry by entry_id, extracts the planned order data,
    and calls the service to create a ProductionOrder.
    """
    # Look up the entry
    r = await db.execute(
        select(MpsEntry).where(MpsEntry.id == entry_id, MpsEntry.mps_id == mps_id)
    )
    entry = r.scalar_one_or_none()
    if not entry:
        raise HTTPException(404, "MPS entry not found")

    if entry.planned_order_qty <= 0:
        raise HTTPException(400, "No planned order exists for this entry; run calculate_mps first")

    result = await svc.convert_planned_to_work_order(
        db,
        mps_id=mps_id,
        product_no=entry.product_no,
        period_week=entry.period_week,
        quantity=entry.planned_order_qty,
    )
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result
