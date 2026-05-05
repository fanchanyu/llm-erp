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
            SupplierResponse(id=str(s.id), name=s.name, contact=s.contact,
                             phone=s.phone, email=s.email) for s in suppliers
        ],
        "total": total,
    }


@router.post("/suppliers", response_model=SupplierResponse, status_code=201)
async def create_supplier(data: SupplierCreate, db: AsyncSession = Depends(get_db)):
    s = await svc.create_supplier(db, data.name, data.contact, data.phone, data.email)
    return SupplierResponse(id=str(s.id), name=s.name, contact=s.contact,
                            phone=s.phone, email=s.email)


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

    po = await svc.create_purchase_order(
        db, supplier.id, resolved_items,
        ordered_by=data.ordered_by, notes=data.notes,
    )
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
