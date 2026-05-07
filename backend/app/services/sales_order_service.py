"""Sales Order Service — sales order CRUD with line items."""

from __future__ import annotations
from datetime import datetime, date, timedelta
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.sales_order import SalesOrder, SalesOrderItem
from app.models.customer import Customer


async def list_orders(
    db: AsyncSession,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[SalesOrder], int]:
    """List sales orders with optional status filter and pagination."""
    q = select(SalesOrder).options(selectinload(SalesOrder.items))
    if status:
        q = q.where(SalesOrder.status == status)
    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0
    result = await db.execute(
        q.offset(skip).limit(limit).order_by(SalesOrder.created_at.desc())
    )
    return list(result.scalars().all()), total


async def get_order(db: AsyncSession, order_id: int) -> Optional[SalesOrder]:
    """Get a sales order by ID with items eagerly loaded."""
    result = await db.execute(
        select(SalesOrder)
        .options(selectinload(SalesOrder.items))
        .where(SalesOrder.id == order_id)
    )
    return result.scalar_one_or_none()


async def get_order_by_no(db: AsyncSession, so_no: str) -> Optional[SalesOrder]:
    """Get a sales order by so_no with items eagerly loaded."""
    result = await db.execute(
        select(SalesOrder)
        .options(selectinload(SalesOrder.items))
        .where(SalesOrder.so_no == so_no)
    )
    return result.scalar_one_or_none()


async def _generate_so_no(db: AsyncSession) -> str:
    """Auto-generate SO number like 'SO-20260507-001'."""
    today_str = date.today().strftime("%Y%m%d")
    r = await db.execute(
        select(SalesOrder)
        .where(SalesOrder.so_no.like(f"SO-{today_str}-%"))
        .order_by(SalesOrder.so_no.desc())
        .limit(1)
    )
    last = r.scalar_one_or_none()
    seq = 1
    if last:
        seq = int(last.so_no.split("-")[-1]) + 1
    return f"SO-{today_str}-{seq:03d}"


async def create_order(
    db: AsyncSession,
    customer_no: str,
    items_data: list[dict],
    notes: Optional[str] = None,
) -> SalesOrder:
    """Create a sales order with line items.

    Validates customer exists, auto-generates SO number,
    calculates line totals and order total.
    """
    # Resolve customer
    result = await db.execute(select(Customer).where(Customer.customer_no == customer_no))
    customer = result.scalar_one_or_none()
    if not customer:
        raise ValueError(f"Customer not found: {customer_no}")

    # Generate SO number
    so_no = await _generate_so_no(db)

    # Create order
    order = SalesOrder(
        so_no=so_no,
        customer_id=customer.id,
        status="draft",
        notes=notes,
        total_amount=0,
    )
    db.add(order)
    await db.flush()

    # Create items
    total_amount = 0
    for item_data in items_data:
        unit_price = item_data.get("unit_price", 0)
        quantity = item_data["quantity"]
        line_total = quantity * unit_price
        total_amount += line_total

        item = SalesOrderItem(
            so_id=order.id,
            part_no=item_data["part_no"],
            part_name=item_data.get("part_name"),
            quantity=quantity,
            unit_price=unit_price,
            line_total=line_total,
            delivery_date=item_data.get("delivery_date"),
        )
        db.add(item)

    order.total_amount = total_amount
    await db.flush()

    # Reload with items
    return await get_order(db, order.id)


async def confirm_order(db: AsyncSession, order_id: int) -> SalesOrder:
    """Confirm a sales order: status → confirmed, create production orders in dispatch."""
    from app.services.dispatch_service import create_order as create_dispatch_order

    order = await get_order(db, order_id)
    if not order:
        raise ValueError(f"Sales order {order_id} not found")
    if order.status != "draft":
        raise ValueError(f"Order {order.so_no} already in status: {order.status}")

    order.status = "confirmed"
    await db.flush()

    # Create production orders for each item
    wo_refs = []
    for item in order.items:
        due = item.delivery_date or (date.today() + timedelta(days=30))
        wo = await create_dispatch_order(
            db,
            product_no=item.part_no,
            quantity=float(item.quantity),
            due_date=str(due),
            notes=f"SO:{order.so_no} / {item.part_name or item.part_no}",
            priority=3,
        )
        wo_refs.append(wo.order_no)

    order.status = "production"
    await db.flush()

    # Reload with items
    return await get_order(db, order.id)


async def ship_order(db: AsyncSession, order_id: int) -> SalesOrder:
    """Ship a sales order: status → shipped, auto-outbound inventory."""
    from app.services import inventory_service

    order = await get_order(db, order_id)
    if not order:
        raise ValueError(f"Sales order {order_id} not found")
    if order.status == "shipped":
        raise ValueError(f"Order {order.so_no} already shipped")
    if order.status == "delivered":
        raise ValueError(f"Order {order.so_no} already delivered")

    # Outbound inventory for each item — find stock location first
    for item in order.items:
        part = await inventory_service.get_part_by_no(db, item.part_no)
        if part:
            # Find actual stock location
            from app.models.inventory import Inventory
            stock_q = await db.execute(
                select(Inventory).where(
                    Inventory.part_id == part.id,
                    Inventory.quantity >= float(item.quantity),
                ).order_by(Inventory.updated_at).limit(1)
            )
            stock = stock_q.scalar_one_or_none()
            loc = stock.location if stock else None
            try:
                await inventory_service.outbound(
                    db, part.id, float(item.quantity),
                    location=loc,
                    reference_no=order.so_no,
                    notes=f"SO shipping: {order.so_no} / {item.part_name or item.part_no}",
                    created_by="system",
                )
            except (ValueError, Exception):
                pass  # Insufficient stock — ship what we can

    order.status = "shipped"
    await db.flush()
    return await get_order(db, order_id)


async def deliver_order(db: AsyncSession, order_id: int) -> SalesOrder:
    """Mark sales order as delivered: status → delivered."""
    order = await get_order(db, order_id)
    if not order:
        raise ValueError(f"Sales order {order_id} not found")
    if order.status != "shipped":
        raise ValueError(f"Order {order.so_no} must be shipped first (current: {order.status})")

    order.status = "delivered"
    await db.flush()
    return await get_order(db, order_id)
