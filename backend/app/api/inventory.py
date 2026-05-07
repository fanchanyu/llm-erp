"""Inventory API endpoints with real DB integration."""

import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services import inventory_service as svc
from app.schemas.inventory import (
    PartCreate, PartResponse, StockItem,
    InboundRequest, OutboundRequest, TransactionResponse,
)
from app.event_engine.service_enforcer import ConstraintBlocked

router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.get("/parts", response_model=dict)
async def list_parts(
    search: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    parts, total = await svc.list_parts(db, search, category, skip, limit)
    return {
        "parts": [
            PartResponse(
                id=str(p.id), part_no=p.part_no, name=p.name,
                unit=p.unit, spec=p.spec, category=p.category,
                created_at=p.created_at,
            ) for p in parts
        ],
        "total": total,
    }


@router.post("/parts", response_model=PartResponse, status_code=201)
async def create_part(data: PartCreate, db: AsyncSession = Depends(get_db)):
    existing = await svc.get_part_by_no(db, data.part_no)
    if existing:
        raise HTTPException(400, f"Part {data.part_no} already exists")
    part = await svc.create_part(db, data.part_no, data.name, data.unit, data.spec, data.category)
    return PartResponse(
        id=str(part.id), part_no=part.part_no, name=part.name,
        unit=part.unit, spec=part.spec, category=part.category,
        created_at=part.created_at,
    )


@router.get("/stock", response_model=dict)
async def query_stock(
    part_no: Optional[str] = Query(None),
    name: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    items = await svc.query_stock(db, part_no, name, category)
    return {"items": items, "total": len(items)}


@router.post("/inbound", response_model=dict)
async def inbound(data: InboundRequest, db: AsyncSession = Depends(get_db)):
    part = await svc.get_part_by_no(db, data.part_no)
    if not part:
        raise HTTPException(404, f"Part not found: {data.part_no}")
    inv = await svc.inbound(db, part.id, data.quantity, data.location,
                            data.reference_no, data.notes, "api")
    return {
        "message": f"Inbound {data.quantity} of {data.part_no} OK",
        "location": data.location,
        "new_quantity": float(inv.quantity),
    }


@router.post("/outbound", response_model=dict)
async def outbound(data: OutboundRequest, db: AsyncSession = Depends(get_db)):
    part = await svc.get_part_by_no(db, data.part_no)
    if not part:
        raise HTTPException(404, f"Part not found: {data.part_no}")
    try:
        inv = await svc.outbound(db, part.id, data.quantity, data.location,
                                 data.reference_no, data.notes, "api")
    except ValueError as e:
        raise HTTPException(400, str(e))
    except ConstraintBlocked as e:
        raise HTTPException(422, detail={
            "error": "business_rule_violation",
            "operation": e.operation,
            "verdicts": [
                {"code": v.code, "message": v.message, "alternatives": v.alternatives}
                for v in e.verdicts
            ],
        })
    return {
        "message": f"Outbound {data.quantity} of {data.part_no} OK",
        "location": data.location,
        "new_quantity": float(inv.quantity),
    }


@router.get("/transactions", response_model=dict)
async def list_transactions(
    part_no: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    part_id = None
    if part_no:
        part = await svc.get_part_by_no(db, part_no)
        if part:
            part_id = part.id
    txns = await svc.list_transactions(db, part_id, skip, limit)
    return {
        "transactions": [
            TransactionResponse(
                id=str(t.id), part_id=str(t.part_id), type=t.type,
                quantity=float(t.quantity), reference_no=t.reference_no,
                notes=t.notes, created_by=t.created_by, created_at=t.created_at,
            ) for t in txns
        ],
        "total": len(txns),
    }
