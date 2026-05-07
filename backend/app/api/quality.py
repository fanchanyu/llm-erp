"""Quality (QC) API endpoints with real DB integration."""

import uuid
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services import quality_service as svc
from app.schemas.quality import (
    InspectionCreate, InspectionResponse, InspectionStatusUpdate,
    InspectionResultCreate, InspectionResultResponse,
    NCCreate, NCResponse,
    CAPACreate, CAPAResponse,
)
from app.event_engine.service_enforcer import ConstraintBlocked

router = APIRouter(prefix="/quality", tags=["quality"])


# ─── Inspections ──────────────────────────────────────────────────

@router.get("/inspections", response_model=dict)
async def list_inspections(
    status: Optional[str] = Query(None),
    part_id: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    inspections, total = await svc.list_inspections(db, status, part_id, skip, limit)
    return {
        "inspections": [
            InspectionResponse(
                id=str(i.id), inspection_no=i.inspection_no,
                po_id=str(i.po_id) if i.po_id else None,
                part_id=str(i.part_id),
                lot_no=i.lot_no, quantity=float(i.quantity),
                status=i.status, inspection_date=i.inspection_date,
                inspected_by=i.inspected_by, created_at=i.created_at,
            ) for i in inspections
        ],
        "total": total,
    }


@router.post("/inspections", response_model=InspectionResponse, status_code=201)
async def create_inspection(data: InspectionCreate, db: AsyncSession = Depends(get_db)):
    part_id = uuid.UUID(data.part_id) if isinstance(data.part_id, str) else data.part_id
    po_id = uuid.UUID(data.po_id) if data.po_id else None
    insp = await svc.create_inspection(
        db, data.inspection_no, part_id, data.quantity,
        po_id=po_id, lot_no=data.lot_no,
        inspection_date=data.inspection_date,
        inspected_by=data.inspected_by, actor_role="api",
    )
    return InspectionResponse(
        id=str(insp.id), inspection_no=insp.inspection_no,
        po_id=str(insp.po_id) if insp.po_id else None,
        part_id=str(insp.part_id),
        lot_no=insp.lot_no, quantity=float(insp.quantity),
        status=insp.status, inspection_date=insp.inspection_date,
        inspected_by=insp.inspected_by, created_at=insp.created_at,
    )


@router.patch("/inspections/{inspection_id}/status", response_model=InspectionResponse)
async def update_inspection_status(
    inspection_id: str, data: InspectionStatusUpdate,
    db: AsyncSession = Depends(get_db),
):
    try:
        insp = await svc.update_inspection_status(
            db, uuid.UUID(inspection_id), data.status, actor_role="api",
        )
    except ConstraintBlocked as e:
        raise HTTPException(422, detail={
            "error": "business_rule_violation",
            "operation": e.operation,
            "verdicts": [
                {"code": v.code, "message": v.message, "alternatives": v.alternatives}
                for v in e.verdicts
            ],
        })
    if not insp:
        raise HTTPException(404, f"Inspection not found: {inspection_id}")
    return InspectionResponse(
        id=str(insp.id), inspection_no=insp.inspection_no,
        po_id=str(insp.po_id) if insp.po_id else None,
        part_id=str(insp.part_id),
        lot_no=insp.lot_no, quantity=float(insp.quantity),
        status=insp.status, inspection_date=insp.inspection_date,
        inspected_by=insp.inspected_by, created_at=insp.created_at,
    )


@router.post("/inspections/{inspection_id}/results", response_model=InspectionResultResponse, status_code=201)
async def add_inspection_result(
    inspection_id: str, data: InspectionResultCreate,
    db: AsyncSession = Depends(get_db),
):
    result = await svc.add_inspection_result(
        db, uuid.UUID(inspection_id),
        item_no=data.item_no, description=data.description,
        spec_value=data.spec_value, measured_value=data.measured_value,
        result=data.result, notes=data.notes,
    )
    if not result:
        raise HTTPException(404, f"Inspection not found: {inspection_id}")
    return InspectionResultResponse(
        id=str(result.id), inspection_id=str(result.inspection_id),
        item_no=result.item_no, description=result.description,
        spec_value=result.spec_value, measured_value=result.measured_value,
        result=result.result, notes=result.notes,
        created_at=result.created_at,
    )


# ─── Non-Conformances ─────────────────────────────────────────────

@router.get("/ncs", response_model=dict)
async def list_ncs(
    status: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    part_id: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    ncs, total = await svc.list_ncs(db, status, severity, part_id, skip, limit)
    return {
        "ncs": [
            NCResponse(
                id=str(n.id), nc_no=n.nc_no,
                inspection_id=str(n.inspection_id) if n.inspection_id else None,
                part_id=str(n.part_id),
                defect_code=n.defect_code, description=n.description,
                severity=n.severity, status=n.status,
                created_by=n.created_by, created_at=n.created_at,
                resolved_at=n.resolved_at,
            ) for n in ncs
        ],
        "total": total,
    }


@router.post("/ncs", response_model=NCResponse, status_code=201)
async def create_nc(data: NCCreate, db: AsyncSession = Depends(get_db)):
    part_id = uuid.UUID(data.part_id) if isinstance(data.part_id, str) else data.part_id
    inspection_id = uuid.UUID(data.inspection_id) if data.inspection_id else None
    try:
        nc = await svc.create_nc(
            db, data.nc_no, part_id, data.description,
            inspection_id=inspection_id, defect_code=data.defect_code,
            severity=data.severity, created_by=data.created_by,
            actor_role="api",
        )
    except ConstraintBlocked as e:
        raise HTTPException(422, detail={
            "error": "business_rule_violation",
            "operation": e.operation,
            "verdicts": [
                {"code": v.code, "message": v.message, "alternatives": v.alternatives}
                for v in e.verdicts
            ],
        })
    return NCResponse(
        id=str(nc.id), nc_no=nc.nc_no,
        inspection_id=str(nc.inspection_id) if nc.inspection_id else None,
        part_id=str(nc.part_id),
        defect_code=nc.defect_code, description=nc.description,
        severity=nc.severity, status=nc.status,
        created_by=nc.created_by, created_at=nc.created_at,
        resolved_at=nc.resolved_at,
    )


# ─── CAPA ─────────────────────────────────────────────────────────

@router.get("/capas", response_model=dict)
async def list_capas(
    status: Optional[str] = Query(None),
    nc_id: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    capas, total = await svc.list_capas(db, status, nc_id, skip, limit)
    return {
        "capas": [
            CAPAResponse(
                id=str(c.id), nc_id=str(c.nc_id),
                root_cause=c.root_cause, action=c.action,
                responsible=c.responsible, deadline=c.deadline,
                status=c.status, closed_at=c.closed_at,
                created_at=c.created_at,
            ) for c in capas
        ],
        "total": total,
    }


@router.post("/ncs/{nc_id}/capa", response_model=CAPAResponse, status_code=201)
async def create_capa(
    nc_id: str, data: CAPACreate,
    db: AsyncSession = Depends(get_db),
):
    capa = await svc.create_capa(
        db, uuid.UUID(nc_id), data.action,
        root_cause=data.root_cause, responsible=data.responsible,
        deadline=data.deadline, actor_role="api",
    )
    if not capa:
        raise HTTPException(404, f"Non-conformance not found: {nc_id}")
    return CAPAResponse(
        id=str(capa.id), nc_id=str(capa.nc_id),
        root_cause=capa.root_cause, action=capa.action,
        responsible=capa.responsible, deadline=capa.deadline,
        status=capa.status, closed_at=capa.closed_at,
        created_at=capa.created_at,
    )
