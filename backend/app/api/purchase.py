"""Purchase API endpoints with real DB integration."""

import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services import purchase_service as svc
from app.services.inventory_service import get_part_by_no
from app.schemas.purchase import (
    SupplierCreate, SupplierResponse, POCreate, POResponse,
    POItemResponse, POStatusUpdate,
)
from app.event_engine.service_enforcer import ConstraintBlocked

router = APIRouter(prefix="/purchase", tags=["purchase"])


@router.get("/suppliers", response_model=dict)
async def list_suppliers(
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    suppliers, total = await svc.list_suppliers(db, search, skip, limit)
    return {
        "suppliers": [
            SupplierResponse(
                id=str(s.id), name=s.name, tier=s.tier or "1",
                parent_supplier_name=s.parent_supplier.name if s.parent_supplier else None,
                sub_supplier_count=len(s.sub_suppliers) if s.sub_suppliers else 0,
                contact=s.contact, phone=s.phone, email=s.email, score=s.score
            ) for s in suppliers
        ],
        "total": total,
    }


@router.patch("/suppliers/{supplier_id}/score")
async def update_supplier_score(supplier_id: str, score: float,
                                db: AsyncSession = Depends(get_db)):
    """Update supplier quality score. Locks supplier if score < 2.0."""
    try:
        uid = uuid.UUID(supplier_id)
    except ValueError:
        raise HTTPException(400, "Invalid supplier ID")
    s = await svc.update_supplier_score(db, uid, score)
    if not s:
        raise HTTPException(404, "Supplier not found")
    msg = f"供應商 {s.name} 評分更新為 {score}"
    if score < 2.0:
        msg += " — 評分低於2.0，已自動鎖定"
    elif score < 3.0:
        msg += " — 評分低於3.0，建議留意"
    return {"message": msg, "score": s.score, "locked": score < 2.0}


@router.post("/suppliers", response_model=SupplierResponse, status_code=201)
async def create_supplier(data: SupplierCreate, db: AsyncSession = Depends(get_db)):
    parent_id = None
    if data.parent_supplier_name:
        parents, _ = await svc.list_suppliers(db, data.parent_supplier_name)
        if parents:
            parent_id = parents[0].id
    s = await svc.create_supplier(db, data.name, data.contact, data.phone, data.email,
                                   tier=data.tier, parent_supplier_id=parent_id)
    return SupplierResponse(
        id=str(s.id), name=s.name, tier=s.tier or "1",
        parent_supplier_name=s.parent_supplier.name if s.parent_supplier else None,
        sub_supplier_count=len(s.sub_suppliers) if s.sub_suppliers else 0,
        contact=s.contact, phone=s.phone, email=s.email
    )


@router.get("/orders", response_model=dict)
async def list_orders(
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    orders, total = await svc.list_purchase_orders(db, status, skip, limit)
    result = []
    for po in orders:
        supplier_name = po.supplier.name if po.supplier else ""
        items = []
        for item in po.items:
            items.append(POItemResponse(
                id=str(item.id), part_no=item.part.part_no if item.part else "",
                part_name=item.part.name if item.part else "",
                quantity=float(item.quantity), unit_price=float(item.unit_price) if item.unit_price else None,
                expected_delivery=item.expected_delivery,
                received_qty=float(item.received_qty or 0),
            ))
        result.append(POResponse(
            id=str(po.id), po_no=po.po_no, supplier_name=supplier_name,
            status=po.status, items=items, ordered_by=po.ordered_by,
            notes=po.notes, created_at=po.created_at,
        ))
    return {"orders": result, "total": total}


@router.post("/orders", status_code=201)
async def create_order(data: POCreate, db: AsyncSession = Depends(get_db)):
    # Find or create supplier
    suppliers, _ = await svc.list_suppliers(db, data.supplier_name)
    supplier = suppliers[0] if suppliers else None
    if not supplier:
        supplier = await svc.create_supplier(db, data.supplier_name)

    # Resolve part IDs
    resolved_items = []
    for item in data.items:
        part = await get_part_by_no(db, item.part_no)
        if not part:
            raise HTTPException(404, f"Part not found: {item.part_no}")
        resolved_items.append({
            "part_id": part.id,
            "quantity": item.quantity,
            "unit_price": item.unit_price,
            "expected_delivery": item.expected_delivery,
        })

    try:
        po = await svc.create_purchase_order(
            db, supplier.id, resolved_items,
            ordered_by=data.ordered_by, notes=data.notes,
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
    return {
        "message": f"Purchase order {po.po_no} created",
        "po_no": po.po_no,
        "id": str(po.id),
        "status": po.status,
    }


@router.patch("/orders/{order_id}/status")
async def update_order_status(order_id: str, data: POStatusUpdate,
                              db: AsyncSession = Depends(get_db)):
    try:
        uid = uuid.UUID(order_id)
    except ValueError:
        raise HTTPException(400, "Invalid order ID")
    po = await svc.update_po_status(db, uid, data.status)
    if not po:
        raise HTTPException(404, "Purchase order not found")
    return {"message": f"PO {po.po_no} status → {po.status}", "po_no": po.po_no, "status": po.status}
