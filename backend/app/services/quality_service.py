"""Quality service — inspection orders, NCs, and CAPA CRUD."""
from __future__ import annotations
import uuid
from datetime import datetime, date
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.quality import InspectionOrder, InspectionResult, NonConformance, CAPARecord
from app.event_engine.service_enforcer import enforce
from app.event_engine.event_bus import get_bus
from app.event_engine.events import nc_created


# ─── Inspection Orders ────────────────────────────────────────────

async def list_inspections(
    db: AsyncSession,
    status: Optional[str] = None,
    part_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[InspectionOrder], int]:
    """List/search inspection orders with pagination."""
    q = select(InspectionOrder).options(selectinload(InspectionOrder.part))
    if status:
        q = q.where(InspectionOrder.status == status)
    if part_id:
        q = q.where(InspectionOrder.part_id == part_id)
    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0
    result = await db.execute(
        q.offset(skip).limit(limit).order_by(InspectionOrder.created_at.desc())
    )
    return list(result.scalars().all()), total


async def get_inspection(db: AsyncSession, inspection_id: uuid.UUID) -> Optional[InspectionOrder]:
    return await db.get(InspectionOrder, inspection_id)


async def _next_inspection_no(db: AsyncSession) -> str:
    """Generate next inspection number: IQC-YYYYMMDD-XXX."""
    today = datetime.utcnow().strftime("%Y%m%d")
    result = await db.execute(
        select(func.count()).select_from(
            select(InspectionOrder).where(
                InspectionOrder.inspection_no.like(f"IQC-{today}-%")
            ).subquery()
        )
    )
    count = result.scalar() or 0
    return f"IQC-{today}-{count + 1:03d}"


async def create_inspection(
    db: AsyncSession,
    inspection_no: str,
    part_id: uuid.UUID,
    quantity: float,
    po_id: Optional[uuid.UUID] = None,
    lot_no: Optional[str] = None,
    inspection_date: Optional[datetime] = None,
    inspected_by: Optional[str] = None,
    actor_role: str = "",
) -> InspectionOrder:
    """Create inspection order and emit notification event."""
    insp = InspectionOrder(
        inspection_no=inspection_no or await _next_inspection_no(db),
        po_id=po_id,
        part_id=part_id,
        lot_no=lot_no,
        quantity=quantity,
        status="pending",
        inspection_date=inspection_date,
        inspected_by=inspected_by,
    )
    db.add(insp)
    await db.flush()

    # Emit notification event
    bus = get_bus()
    from app.event_engine.events import DomainEvent, EventCategory
    bus.emit(DomainEvent(
        event_type="inspection.created",
        category=EventCategory.QUALITY,
        actor_role=actor_role,
        aggregate_id=insp.inspection_no,
        aggregate_type="inspection_order",
        payload={"part_id": str(part_id), "quantity": quantity},
        metadata={"notification_targets": ["quality", "warehouse"]},
    ))
    return insp


async def update_inspection_status(
    db: AsyncSession,
    inspection_id: uuid.UUID,
    status: str,
    actor_role: str = "",
) -> Optional[InspectionOrder]:
    """Update inspection status. When rejected, runs enforce('issue_qc_hold')."""
    insp = await db.get(InspectionOrder, inspection_id)
    if not insp:
        return None

    if status == "rejected":
        enforce("issue_qc_hold", {
            "inspection_no": insp.inspection_no,
            "part_id": str(insp.part_id),
            "quantity": float(insp.quantity),
        }, actor_role=actor_role)

    insp.status = status
    await db.flush()
    return insp


# ─── Inspection Results ───────────────────────────────────────────

async def add_inspection_result(
    db: AsyncSession,
    inspection_id: uuid.UUID,
    item_no: Optional[str] = None,
    description: Optional[str] = None,
    spec_value: Optional[str] = None,
    measured_value: Optional[str] = None,
    result: str = "pass",
    notes: Optional[str] = None,
) -> Optional[InspectionResult]:
    """Add an inspection result record."""
    insp = await db.get(InspectionOrder, inspection_id)
    if not insp:
        return None

    ir = InspectionResult(
        inspection_id=inspection_id,
        item_no=item_no,
        description=description,
        spec_value=spec_value,
        measured_value=measured_value,
        result=result,
        notes=notes,
    )
    db.add(ir)
    await db.flush()
    return ir


# ─── Non-Conformances ─────────────────────────────────────────────

async def list_ncs(
    db: AsyncSession,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    part_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[NonConformance], int]:
    """List non-conformances with pagination."""
    q = select(NonConformance).options(selectinload(NonConformance.part))
    if status:
        q = q.where(NonConformance.status == status)
    if severity:
        q = q.where(NonConformance.severity == severity)
    if part_id:
        q = q.where(NonConformance.part_id == part_id)
    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0
    result = await db.execute(
        q.offset(skip).limit(limit).order_by(NonConformance.created_at.desc())
    )
    return list(result.scalars().all()), total


async def get_nc(db: AsyncSession, nc_id: uuid.UUID) -> Optional[NonConformance]:
    return await db.get(NonConformance, nc_id)


async def _next_nc_no(db: AsyncSession) -> str:
    """Generate next NC number: NC-YYYYMMDD-XXX."""
    today = datetime.utcnow().strftime("%Y%m%d")
    result = await db.execute(
        select(func.count()).select_from(
            select(NonConformance).where(
                NonConformance.nc_no.like(f"NC-{today}-%")
            ).subquery()
        )
    )
    count = result.scalar() or 0
    return f"NC-{today}-{count + 1:03d}"


async def create_nc(
    db: AsyncSession,
    nc_no: str,
    part_id: uuid.UUID,
    description: str,
    inspection_id: Optional[uuid.UUID] = None,
    defect_code: Optional[str] = None,
    severity: str = "minor",
    created_by: Optional[str] = None,
    actor_role: str = "",
) -> NonConformance:
    """Create non-conformance. Runs enforce('create_nc') and emits nc_created event."""
    enforce("create_nc", {
        "defect_code": defect_code or "",
        "severity": severity,
    }, actor_role=actor_role)

    nc = NonConformance(
        nc_no=nc_no or await _next_nc_no(db),
        inspection_id=inspection_id,
        part_id=part_id,
        defect_code=defect_code,
        description=description,
        severity=severity,
        status="open",
        created_by=created_by,
    )
    db.add(nc)
    await db.flush()

    # Emit nc_created domain event
    bus = get_bus()
    event = nc_created(
        nc_ref=nc.nc_no,
        item=str(part_id),
        defect=defect_code or description[:50],
        severity=severity,
        actor_role=actor_role,
    )
    bus.emit(event)
    return nc


# ─── CAPA Records ─────────────────────────────────────────────────

async def list_capas(
    db: AsyncSession,
    status: Optional[str] = None,
    nc_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[CAPARecord], int]:
    """List CAPA records with pagination."""
    q = select(CAPARecord).options(selectinload(CAPARecord.nc))
    if status:
        q = q.where(CAPARecord.status == status)
    if nc_id:
        q = q.where(CAPARecord.nc_id == nc_id)
    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0
    result = await db.execute(
        q.offset(skip).limit(limit).order_by(CAPARecord.created_at.desc())
    )
    return list(result.scalars().all()), total


async def create_capa(
    db: AsyncSession,
    nc_id: uuid.UUID,
    action: str,
    root_cause: Optional[str] = None,
    responsible: Optional[str] = None,
    deadline: Optional[date] = None,
    actor_role: str = "",
) -> Optional[CAPARecord]:
    """Create a CAPA record linked to an NC."""
    nc = await db.get(NonConformance, nc_id)
    if not nc:
        return None

    capa = CAPARecord(
        nc_id=nc_id,
        root_cause=root_cause,
        action=action,
        responsible=responsible,
        deadline=deadline,
        status="planned",
    )
    db.add(capa)
    await db.flush()

    # Update NC status to investigating
    if nc.status == "open":
        nc.status = "investigating"
        await db.flush()

    # Emit event
    bus = get_bus()
    from app.event_engine.events import DomainEvent, EventCategory
    bus.emit(DomainEvent(
        event_type="capa.created",
        category=EventCategory.QUALITY,
        actor_role=actor_role,
        aggregate_id=str(capa.id),
        aggregate_type="capa",
        payload={"nc_no": nc.nc_no, "action": action},
        metadata={"notification_targets": ["quality", "production"]},
    ))
    return capa
