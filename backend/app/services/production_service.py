"""
Production Service — Phase A enhancements for Work Order management,
MPS (Master Production Schedule), Shop Floor Control, and WIP tracking.

Extends the existing dispatch_service with higher-level production features.
"""

from __future__ import annotations
import uuid
from datetime import datetime, date, timedelta
from typing import Optional
from sqlalchemy import select, and_, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.dispatch import (
    ProductionOrder, Operation, WorkCenter, DispatchLog,
    OrderStatus, OpStatus, WCStatus,
)
from app.models.organization import Employee
from app.services import dispatch_service as dispatch_svc
from app.event_engine.service_enforcer import enforce


# ═══════════════════════════════════════════════════════════════════
# ─── WORK ORDER LIFECYCLE (Enhanced) ──────────────────────────────
# ═══════════════════════════════════════════════════════════════════

async def create_work_order_from_so(
    db: AsyncSession, so_no: str, so_id: str, customer_name: str,
    product_no: str, product_name: str, quantity: float, due_date: date,
    created_by: str = "system",
) -> ProductionOrder:
    """Create a work order from a sales order. Links back to the SO."""
    kw = {
        "product_no": product_no,
        "product_name": product_name,
        "quantity": quantity,
        "due_date": due_date,
        "so_id": so_id,
        "so_no": so_no,
        "created_by": created_by,
    }
    po = await dispatch_svc.create_order(db, **kw)
    return po


async def start_work_order(
    db: AsyncSession, order_no: str, actor_role: str = "",
) -> dict:
    """Start production on a work order. Sets started_at and status to in_progress."""
    po = await dispatch_svc.get_order(db, order_no=order_no)
    if not po:
        return {"error": f"Order {order_no} not found"}
    if po.status not in (OrderStatus.DISPATCHED.value, OrderStatus.RELEASED.value):
        return {"error": f"Order status must be 'dispatched' or 'released', got '{po.status}'"}

    po.status = OrderStatus.IN_PROGRESS.value
    po.started_at = datetime.utcnow()
    await db.flush()

    return {
        "order_no": po.order_no,
        "status": po.status,
        "started_at": po.started_at.isoformat(),
        "message": f"工單 {po.order_no} 已開工",
    }


async def report_operation_progress(
    db: AsyncSession, order_no: str, operation_seq: int,
    completed_qty: float, operator_id: Optional[str] = None,
    operator_name: str = "",
    actual_start: Optional[datetime] = None,
    actual_end: Optional[datetime] = None,
) -> dict:
    """Report progress on a specific operation (報工)."""
    po = await dispatch_svc.get_order(db, order_no=order_no)
    if not po:
        return {"error": f"Order {order_no} not found"}

    op = None
    for o in po.operations:
        if o.sequence_no == operation_seq:
            op = o
            break
    if not op:
        return {"error": f"Operation seq {operation_seq} not found in order {order_no}"}

    op.completed_qty = completed_qty
    if operator_id:
        op.operator_id = operator_id
    if operator_name:
        op.operator_name = operator_name
    if actual_start:
        op.actual_start = actual_start
    if actual_end:
        op.actual_end = actual_end

    # Auto-set status based on completion
    if completed_qty >= po.quantity:
        op.status = OpStatus.COMPLETED.value
    elif completed_qty > 0:
        op.status = OpStatus.RUNNING.value
        op.actual_start = actual_start or datetime.utcnow()

    await db.flush()

    return {
        "order_no": order_no,
        "operation_seq": operation_seq,
        "completed_qty": completed_qty,
        "total_qty": po.quantity,
        "status": op.status,
        "operator": operator_name or operator_id or "",
    }


async def close_work_order(
    db: AsyncSession, order_no: str,
    completed_qty: float, scrapped_qty: float = 0,
    material_cost: float = 0, bom_cost: float = 0,
    notes: str = "", actor_role: str = "",
) -> dict:
    """
    Close a work order with actual production data.
    Runs constraint checks on yield and cost variance.
    """
    po = await dispatch_svc.get_order(db, order_no=order_no)
    if not po:
        return {"error": f"Order {order_no} not found"}
    if po.status != OrderStatus.IN_PROGRESS.value:
        return {"error": f"Order must be 'in_progress' to close, got '{po.status}'"}

    # Constraint enforcement
    enforce("close_wo", {
        "planned_qty": po.quantity,
        "produced_qty": completed_qty,
        "scrapped_qty": scrapped_qty,
        "material_cost": material_cost,
        "bom_cost": bom_cost,
    }, actor_role=actor_role)

    po.completed_qty = completed_qty
    po.scrapped_qty = scrapped_qty
    po.status = OrderStatus.COMPLETED.value
    po.completed_at = datetime.utcnow()
    if notes:
        po.notes = (po.notes or "") + f"\n[Close] {notes}"

    # Log
    log = DispatchLog(
        order_id=po.id,
        action="close",
        notes=f"Closed: {completed_qty} produced, {scrapped_qty} scrapped",
    )
    db.add(log)
    await db.flush()

    yield_pct = round(completed_qty / po.quantity * 100, 1) if po.quantity > 0 else 0
    return {
        "order_no": po.order_no,
        "status": "completed",
        "planned_qty": po.quantity,
        "completed_qty": completed_qty,
        "scrapped_qty": scrapped_qty,
        "yield_pct": yield_pct,
        "completed_at": po.completed_at.isoformat(),
    }


# ═══════════════════════════════════════════════════════════════════
# ─── MPS (Master Production Schedule) ─────────────────────────────
# ═══════════════════════════════════════════════════════════════════

async def get_mps(
    db: AsyncSession,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    status: Optional[str] = None,
) -> dict:
    """
    Master Production Schedule — aggregate view of planned production.
    Groups work orders by product and date range.
    """
    q = select(ProductionOrder).options(selectinload(ProductionOrder.operations))
    conditions = []
    if start_date:
        conditions.append(ProductionOrder.due_date >= start_date)
    if end_date:
        conditions.append(ProductionOrder.due_date <= end_date)
    if status:
        conditions.append(ProductionOrder.status == status)
    if conditions:
        q = q.where(and_(*conditions))

    result = await db.execute(q.order_by(ProductionOrder.due_date, ProductionOrder.priority))
    orders = list(result.scalars().all())

    # Aggregate by product
    products = {}
    total_planned = 0
    total_completed = 0
    total_wip = 0

    for o in orders:
        if o.product_no not in products:
            products[o.product_no] = {
                "product_no": o.product_no,
                "product_name": o.product_name,
                "total_qty": 0,
                "completed_qty": 0,
                "open_qty": 0,
                "order_count": 0,
            }
        p = products[o.product_no]
        p["total_qty"] += o.quantity
        p["completed_qty"] += o.completed_qty or 0
        p["open_qty"] += (o.quantity - (o.completed_qty or 0))
        p["order_count"] += 1
        total_planned += o.quantity
        total_completed += o.completed_qty or 0
        if o.status == OrderStatus.IN_PROGRESS.value:
            total_wip += o.quantity

    return {
        "period": {
            "start": start_date.isoformat() if start_date else None,
            "end": end_date.isoformat() if end_date else None,
        },
        "summary": {
            "total_orders": len(orders),
            "total_planned_qty": total_planned,
            "total_completed_qty": total_completed,
            "total_wip_qty": total_wip,
            "completion_pct": round(total_completed / total_planned * 100, 1) if total_planned > 0 else 0,
        },
        "products": list(products.values()),
        "orders": [
            {
                "order_no": o.order_no,
                "product_no": o.product_no,
                "product_name": o.product_name,
                "quantity": o.quantity,
                "completed_qty": o.completed_qty or 0,
                "due_date": o.due_date.isoformat() if o.due_date else None,
                "priority": o.priority,
                "status": o.status,
                "so_no": o.so_no,
                "operations": len(o.operations),
            }
            for o in orders
        ],
    }


async def get_mps_gantt_data(
    db: AsyncSession,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> list[dict]:
    """
    Returns data formatted for Gantt chart rendering.
    Groups operations by work center, showing each as a bar.
    """
    q = select(Operation).options(
        selectinload(Operation.work_center),
        selectinload(Operation.order),
    )
    conditions = [Operation.status.in_([OpStatus.READY.value, OpStatus.RUNNING.value,
                                         OpStatus.COMPLETED.value, OpStatus.PAUSED.value])]
    if start_date:
        conditions.append(Operation.scheduled_start >= datetime.combine(start_date, datetime.min.time()))
    if end_date:
        conditions.append(Operation.scheduled_end <= datetime.combine(end_date, datetime.max.time()))

    result = await db.execute(q.where(and_(*conditions)).order_by(Operation.scheduled_start))
    ops = list(result.scalars().all())

    # Group by work center
    wc_groups = {}
    for op in ops:
        wc_name = op.work_center.name if op.work_center else "Unknown"
        if wc_name not in wc_groups:
            wc_groups[wc_name] = {
                "work_center": wc_name,
                "status": op.work_center.status if op.work_center else "idle",
                "operations": [],
            }
        status_color = {
            "completed": "green",
            "running": "blue",
            "ready": "orange",
            "pending": "gray",
            "paused": "yellow",
        }.get(op.status, "gray")

        wc_groups[wc_name]["operations"].append({
            "order_no": op.order.order_no if op.order else "",
            "product_no": op.order.product_no if op.order else "",
            "operation_seq": op.sequence_no,
            "operation_name": op.name or "",
            "status": op.status,
            "color": status_color,
            "scheduled_start": op.scheduled_start.isoformat() if op.scheduled_start else None,
            "scheduled_end": op.scheduled_end.isoformat() if op.scheduled_end else None,
            "duration_min": op.total_time_min,
            "completed_qty": op.completed_qty or 0,
            "operator_name": op.operator_name or "",
        })

    return list(wc_groups.values())


# ═══════════════════════════════════════════════════════════════════
# ─── SHOP FLOOR CONTROL ──────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════

async def get_shop_floor_summary(db: AsyncSession) -> dict:
    """Aggregate shop floor status: machine utilization, operator workload, WIP."""

    # Machine stats
    wc_result = await db.execute(select(WorkCenter))
    work_centers = list(wc_result.scalars().all())
    total_machines = len(work_centers)
    running_machines = sum(1 for w in work_centers if w.status == WCStatus.RUNNING.value)
    down_machines = sum(1 for w in work_centers if w.status == WCStatus.DOWN.value)
    idle_machines = sum(1 for w in work_centers if w.status == WCStatus.IDLE.value)

    # Work order stats
    wo_result = await db.execute(select(ProductionOrder))
    all_orders = list(wo_result.scalars().all())
    active_orders = [o for o in all_orders if o.status in (
        OrderStatus.RELEASED.value, OrderStatus.DISPATCHED.value, OrderStatus.IN_PROGRESS.value)]
    overdue_orders = [o for o in active_orders if o.due_date and date.today() > o.due_date]
    wip_orders = [o for o in all_orders if o.status == OrderStatus.IN_PROGRESS.value]
    wip_qty = sum(o.quantity - (o.completed_qty or 0) for o in wip_orders)
    completed_today = [o for o in all_orders
                       if o.status == OrderStatus.COMPLETED.value
                       and o.completed_at
                       and o.completed_at.date() == date.today()]

    # Active operations
    op_result = await db.execute(
        select(Operation).where(
            Operation.status.in_([OpStatus.RUNNING.value, OpStatus.READY.value])
        )
    )
    active_ops = list(op_result.scalars().all())

    return {
        "machines": {
            "total": total_machines,
            "running": running_machines,
            "idle": idle_machines,
            "down": down_machines,
            "utilization_pct": round(running_machines / total_machines * 100, 1) if total_machines > 0 else 0,
        },
        "orders": {
            "active": len(active_orders),
            "overdue": len(overdue_orders),
            "wip_orders": len(wip_orders),
            "wip_quantity": wip_qty,
            "completed_today": len(completed_today),
        },
        "operations": {
            "running": sum(1 for o in active_ops if o.status == OpStatus.RUNNING.value),
            "ready": sum(1 for o in active_ops if o.status == OpStatus.READY.value),
        },
    }


async def get_operator_workload(db: AsyncSession) -> list[dict]:
    """Show workload per operator — how many operations assigned vs completed."""
    op_result = await db.execute(
        select(Operation).where(
            Operation.operator_id.isnot(None),
            Operation.operator_name != "",
        )
    )
    all_ops = list(op_result.scalars().all())

    workloads = {}
    for op in all_ops:
        key = op.operator_id or op.operator_name
        if key not in workloads:
            workloads[key] = {
                "operator_id": op.operator_id or "",
                "operator_name": op.operator_name,
                "assigned_ops": 0,
                "completed_ops": 0,
                "running_ops": 0,
                "total_hours": 0,
            }
        w = workloads[key]
        w["assigned_ops"] += 1
        if op.status == OpStatus.COMPLETED.value:
            w["completed_ops"] += 1
        elif op.status == OpStatus.RUNNING.value:
            w["running_ops"] += 1
        w["total_hours"] += round(op.total_time_min / 60, 1)

    return list(workloads.values())


async def get_machine_schedule(
    db: AsyncSession, work_center_name: Optional[str] = None,
) -> list[dict]:
    """Get the current schedule for one or all work centers."""
    q = select(Operation).options(
        selectinload(Operation.work_center),
        selectinload(Operation.order),
    ).where(
        Operation.status.in_([OpStatus.PENDING.value, OpStatus.READY.value,
                               OpStatus.RUNNING.value, OpStatus.PAUSED.value])
    ).order_by(Operation.scheduled_start)

    result = await db.execute(q)
    ops = list(result.scalars().all())

    schedule = []
    for op in ops:
        if work_center_name and (not op.work_center or op.work_center.name != work_center_name):
            continue
        schedule.append({
            "work_center": op.work_center.name if op.work_center else "",
            "order_no": op.order.order_no if op.order else "",
            "product_no": op.order.product_no if op.order else "",
            "operation_seq": op.sequence_no,
            "operation_name": op.name or "",
            "status": op.status,
            "scheduled_start": op.scheduled_start.isoformat() if op.scheduled_start else None,
            "scheduled_end": op.scheduled_end.isoformat() if op.scheduled_end else None,
            "duration_min": op.total_time_min,
            "operator": op.operator_name or "",
            "delay_min": op.delay_minutes or 0,
        })

    return schedule
