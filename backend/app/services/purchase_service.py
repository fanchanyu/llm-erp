"""Purchase service — suppliers and purchase orders CRUD."""
from __future__ import annotations
import uuid
from datetime import datetime, date
from typing import Optional
from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.purchase import Supplier, PurchaseOrder, PurchaseOrderItem
from app.event_engine.service_enforcer import enforce


# ─── Suppliers ────────────────────────────────────────────────────

async def list_suppliers(db: AsyncSession, search: Optional[str] = None,
                         skip: int = 0, limit: int = 50) -> tuple[list[Supplier], int]:
    q = select(Supplier).options(selectinload(Supplier.parent_supplier))
    if search:
        q = q.where(Supplier.name.ilike(f"%{search}%"))
    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0
    result = await db.execute(q.offset(skip).limit(limit).order_by(Supplier.name))
    return list(result.scalars().all()), total


async def get_supplier(db: AsyncSession, supplier_id: uuid.UUID) -> Optional[Supplier]:
    return await db.get(Supplier, supplier_id)


async def create_supplier(db: AsyncSession, name: str, contact: Optional[str] = None,
                          phone: Optional[str] = None, email: Optional[str] = None,
                          score: float = 5.0, tier: str = "1",
                          parent_supplier_id: Optional[uuid.UUID] = None) -> Supplier:
    s = Supplier(name=name, contact=contact, phone=phone, email=email,
                 score=score, tier=tier, parent_supplier_id=parent_supplier_id)
    db.add(s)
    await db.flush()
    return s


async def update_supplier_score(db: AsyncSession, supplier_id: uuid.UUID,
                                score: float) -> Optional[Supplier]:
    s = await db.get(Supplier, supplier_id)
    if not s:
        return None
    s.score = score
    await db.flush()
    return s


# ─── Purchase Orders ──────────────────────────────────────────────

async def list_purchase_orders(db: AsyncSession, status: Optional[str] = None,
                               skip: int = 0, limit: int = 50) -> tuple[list[PurchaseOrder], int]:
    q = select(PurchaseOrder).options(
        selectinload(PurchaseOrder.supplier),
        selectinload(PurchaseOrder.items).selectinload(PurchaseOrderItem.part),
    )
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
    actor_role: str = "",
) -> PurchaseOrder:
    """Create PO with items. Runs constraint checks before execution.

    items = [{part_id, quantity, unit_price?, expected_delivery?}]
    Raises ConstraintBlocked if business rules are violated.
    """
    # Calculate total amount for constraint check
    total_amount = sum(
        (i.get("unit_price") or 0) * i["quantity"]
        for i in items
    )

    # Get supplier for score check
    supplier = await db.get(Supplier, supplier_id)
    supplier_score = getattr(supplier, 'score', 5.0) if supplier else 5.0

    # Run constraint enforcement
    enforce("create_po", {
        "amount": total_amount,
        "supplier_score": supplier_score,
    }, actor_role=actor_role)

    # If we get here, all checks passed
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
                                  quantity: float,
                                  actor_role: str = "") -> Optional[PurchaseOrderItem]:
    item = await db.get(PurchaseOrderItem, item_id)
    if not item:
        return None

    # Check over-receipt constraint
    already_received = float(item.received_qty or 0)
    total_received = already_received + quantity
    enforce("receive_po", {
        "po_qty": float(item.quantity),
        "receipt_qty": total_received,
    }, actor_role=actor_role)

    item.received_qty = total_received
    await db.flush()
    return item
