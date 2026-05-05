"""Purchase service — suppliers and purchase orders CRUD."""

import uuid
from datetime import datetime, date
from typing import Optional
from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.purchase import Supplier, PurchaseOrder, PurchaseOrderItem


# ─── Suppliers ────────────────────────────────────────────────────

async def list_suppliers(db: AsyncSession, search: Optional[str] = None,
                         skip: int = 0, limit: int = 50) -> tuple[list[Supplier], int]:
    q = select(Supplier)
    if search:
        q = q.where(Supplier.name.ilike(f"%{search}%"))
    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0
    result = await db.execute(q.offset(skip).limit(limit).order_by(Supplier.name))
    return list(result.scalars().all()), total


async def get_supplier(db: AsyncSession, supplier_id: uuid.UUID) -> Optional[Supplier]:
    return await db.get(Supplier, supplier_id)


async def create_supplier(db: AsyncSession, name: str, contact: Optional[str] = None,
                          phone: Optional[str] = None, email: Optional[str] = None) -> Supplier:
    s = Supplier(name=name, contact=contact, phone=phone, email=email)
    db.add(s)
    await db.flush()
    return s


# ─── Purchase Orders ──────────────────────────────────────────────

async def list_purchase_orders(db: AsyncSession, status: Optional[str] = None,
                               skip: int = 0, limit: int = 50) -> tuple[list[PurchaseOrder], int]:
    q = select(PurchaseOrder).options(selectinload(PurchaseOrder.supplier))
    if status:
        q = q.where(PurchaseOrder.status == status)
    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0
    result = await db.execute(q.offset(skip).limit(limit).order_by(PurchaseOrder.created_at.desc()))
    return list(result.scalars().all()), total


async def get_purchase_order(db: AsyncSession, po_id: uuid.UUID) -> Optional[PurchaseOrder]:
    return await db.get(PurchaseOrder, po_id)


async def _next_po_no(db: AsyncSession) -> str:
    """Generate next PO number: PO-YYYYMMDD-XXX."""
    today = datetime.utcnow().strftime("%Y%m%d")
    result = await db.execute(
        select(func.count()).select_from(
            select(PurchaseOrder).where(PurchaseOrder.po_no.like(f"PO-{today}-%")).subquery()
        )
    )
    count = result.scalar() or 0
    return f"PO-{today}-{count + 1:03d}"


async def create_purchase_order(
    db: AsyncSession, supplier_id: uuid.UUID, items: list[dict],
    ordered_by: Optional[str] = None, notes: Optional[str] = None,
) -> PurchaseOrder:
    """Create PO with items. items = [{part_id, quantity, unit_price?, expected_delivery?}]"""
    po_no = await _next_po_no(db)
    po = PurchaseOrder(
        po_no=po_no, supplier_id=supplier_id,
        status="draft", ordered_by=ordered_by, notes=notes,
    )
    db.add(po)
    await db.flush()

    for item_data in items:
        item = PurchaseOrderItem(
            po_id=po.id,
            part_id=item_data["part_id"],
            quantity=item_data["quantity"],
            unit_price=item_data.get("unit_price"),
            expected_delivery=item_data.get("expected_delivery"),
        )
        db.add(item)

    await db.flush()
    return po


async def update_po_status(db: AsyncSession, po_id: uuid.UUID,
                           status: str) -> Optional[PurchaseOrder]:
    po = await db.get(PurchaseOrder, po_id)
    if not po:
        return None
    po.status = status
    await db.flush()
    return po


async def update_po_item_received(db: AsyncSession, item_id: uuid.UUID,
                                  quantity: float) -> Optional[PurchaseOrderItem]:
    item = await db.get(PurchaseOrderItem, item_id)
    if not item:
        return None
    item.received_qty = (item.received_qty or 0) + quantity
    await db.flush()
    return item
