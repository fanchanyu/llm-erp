"""Inventory service — parts, stock, transactions CRUD."""
from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.inventory import Part, Inventory, InventoryTransaction
from app.event_engine.service_enforcer import enforce


# ─── Parts ────────────────────────────────────────────────────────

async def list_parts(
    db: AsyncSession,
    search: Optional[str] = None,
    category: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[Part], int]:
    """List/search parts with pagination. Returns (parts, total_count)."""
    q = select(Part)
    if search:
        q = q.where(or_(Part.part_no.ilike(f"%{search}%"), Part.name.ilike(f"%{search}%")))
    if category:
        q = q.where(Part.category == category)
    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0
    result = await db.execute(q.offset(skip).limit(limit).order_by(Part.part_no))
    return list(result.scalars().all()), total


async def get_part(db: AsyncSession, part_id: uuid.UUID) -> Optional[Part]:
    return await db.get(Part, part_id)


async def get_part_by_no(db: AsyncSession, part_no: str) -> Optional[Part]:
    result = await db.execute(select(Part).where(Part.part_no == part_no))
    return result.scalar_one_or_none()


async def create_part(db: AsyncSession, part_no: str, name: str, unit: str,
                      spec: Optional[str] = None, category: Optional[str] = None) -> Part:
    part = Part(part_no=part_no, name=name, unit=unit, spec=spec, category=category)
    db.add(part)
    await db.flush()
    return part


# ─── Inventory (Stock) ────────────────────────────────────────────

async def query_stock(
    db: AsyncSession,
    part_no: Optional[str] = None,
    name: Optional[str] = None,
    category: Optional[str] = None,
) -> list[dict]:
    """Query current stock levels with part info. Returns list of dicts."""
    q = select(
        Part.part_no, Part.name, Part.spec, Part.unit, Part.category,
        Inventory.location, Inventory.quantity, Inventory.updated_at
    ).join(Inventory, Part.id == Inventory.part_id, isouter=True)

    if part_no:
        q = q.where(Part.part_no.ilike(f"%{part_no}%"))
    if name:
        q = q.where(Part.name.ilike(f"%{name}%"))
    if category:
        q = q.where(Part.category == category)

    result = await db.execute(q.order_by(Part.part_no))
    rows = result.all()
    return [
        {
            "part_no": r.part_no, "name": r.name, "spec": r.spec,
            "unit": r.unit, "category": r.category,
            "location": r.location, "quantity": float(r.quantity or 0),
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        }
        for r in rows
    ]


async def get_stock_by_part(db: AsyncSession, part_id: uuid.UUID) -> float:
    """Get total stock quantity for a part across all locations."""
    result = await db.execute(
        select(func.coalesce(func.sum(Inventory.quantity), 0)).where(Inventory.part_id == part_id)
    )
    return float(result.scalar())


async def inbound(db: AsyncSession, part_id: uuid.UUID, quantity: float,
                  location: Optional[str] = None, reference_no: Optional[str] = None,
                  notes: Optional[str] = None, created_by: Optional[str] = None) -> Inventory:
    """Receive stock into inventory."""
    # Find or create inventory record for this location
    result = await db.execute(
        select(Inventory).where(Inventory.part_id == part_id, Inventory.location == location)
    )
    inv = result.scalar_one_or_none()
    if inv:
        inv.quantity += quantity
        inv.updated_at = datetime.utcnow()
    else:
        inv = Inventory(part_id=part_id, location=location, quantity=quantity)
        db.add(inv)

    # Log transaction
    txn = InventoryTransaction(
        part_id=part_id, type="inbound", quantity=quantity,
        reference_no=reference_no, notes=notes, created_by=created_by,
    )
    db.add(txn)
    await db.flush()
    return inv


async def outbound(db: AsyncSession, part_id: uuid.UUID, quantity: float,
                   location: Optional[str] = None, reference_no: Optional[str] = None,
                   notes: Optional[str] = None, created_by: Optional[str] = None,
                   actor_role: str = "") -> Inventory:
    """Issue stock from inventory. Runs constraint checks before executing.

    Raises ConstraintBlocked if business rules are violated.
    """
    # Get current stock level
    result = await db.execute(
        select(Inventory).where(Inventory.part_id == part_id, Inventory.location == location)
    )
    inv = result.scalar_one_or_none()
    current_qty = float(inv.quantity) if inv else 0

    # Get part info for context
    part = await db.get(Part, part_id)
    item_name = part.name if part else "unknown"

    # Run constraint enforcement BEFORE execution
    enforce("issue_material", {
        "item": item_name,
        "quantity": quantity,
        "on_hand": current_qty,
        "location": location or "",
    }, actor_role=actor_role)

    # If we get here, all checks passed — execute
    if not inv or inv.quantity < quantity:
        raise ValueError(f"Insufficient stock: have {current_qty}, need {quantity}")
    inv.quantity -= quantity
    inv.updated_at = datetime.utcnow()

    txn = InventoryTransaction(
        part_id=part_id, type="outbound", quantity=-quantity,
        reference_no=reference_no, notes=notes, created_by=created_by,
    )
    db.add(txn)
    await db.flush()
    return inv


async def list_transactions(db: AsyncSession, part_id: Optional[uuid.UUID] = None,
                            skip: int = 0, limit: int = 50) -> list[InventoryTransaction]:
    q = select(InventoryTransaction).order_by(InventoryTransaction.created_at.desc())
    if part_id:
        q = q.where(InventoryTransaction.part_id == part_id)
    result = await db.execute(q.offset(skip).limit(limit))
    return list(result.scalars().all())
