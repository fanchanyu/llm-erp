"""
Production API — Phase A: Work Order lifecycle, MPS, Shop Floor Control.
Extends the existing dispatch API with higher-level production management.
"""

from datetime import date, datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services import production_service as svc
from app.services import dispatch_service as dispatch_svc

router = APIRouter(prefix="/production", tags=["production"])


# ═══════════════════════════════════════════════════════════════════
# ─── WORK ORDER LIFECYCLE ────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════

@router.post("/work-orders/from-so", response_model=dict, status_code=201)
async def create_wo_from_so(
    so_no: str = Query(...),
    so_id: str = Query(...),
    product_no: str = Query(...),
    product_name: str = Query(""),
    quantity: float = Query(..., gt=0),
    due_date: str = Query(...),
    customer_name: str = Query(""),
    created_by: str = Query("system"),
    db: AsyncSession = Depends(get_db),
):
    """Create a work order from a sales order."""
    due = date.fromisoformat(due_date)
    po = await svc.create_work_order_from_so(
        db, so_no, so_id, customer_name,
        product_no, product_name, quantity, due, created_by,
    )
    return {
        "order_no": po.order_no,
        "product_no": po.product_no,
        "quantity": po.quantity,
        "due_date": po.due_date.isoformat(),
        "status": po.status,
        "so_no": so_no,
        "message": f"工單 {po.order_no} 已從訂單 {so_no} 建立",
    }


@router.post("/work-orders/{order_no}/start", response_model=dict)
async def start_work_order(
    order_no: str,
    actor_role: str = Query(""),
    db: AsyncSession = Depends(get_db),
):
    """Start production on a work order."""
    result = await svc.start_work_order(db, order_no, actor_role)
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@router.post("/work-orders/{order_no}/operation/{seq}/report", response_model=dict)
async def report_progress(
    order_no: str,
    seq: int,
    completed_qty: float = Query(..., gt=0),
    operator_name: str = Query(""),
    operator_id: str = Query(""),
    actual_start: Optional[str] = Query(None),
    actual_end: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Report operation progress (報工)."""
    a_start = datetime.fromisoformat(actual_start) if actual_start else None
    a_end = datetime.fromisoformat(actual_end) if actual_end else None
    result = await svc.report_operation_progress(
        db, order_no, seq, completed_qty,
        operator_id=operator_id or None,
        operator_name=operator_name,
        actual_start=a_start, actual_end=a_end,
    )
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@router.post("/work-orders/{order_no}/close", response_model=dict)
async def close_work_order(
    order_no: str,
    completed_qty: float = Query(..., gt=0),
    scrapped_qty: float = Query(0, ge=0),
    material_cost: float = Query(0),
    bom_cost: float = Query(0),
    notes: str = Query(""),
    actor_role: str = Query(""),
    db: AsyncSession = Depends(get_db),
):
    """Close a work order with actual production data."""
    result = await svc.close_work_order(
        db, order_no, completed_qty, scrapped_qty,
        material_cost, bom_cost, notes, actor_role,
    )
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


# ═══════════════════════════════════════════════════════════════════
# ─── MPS (Master Production Schedule) ─────────────────────────────
# ═══════════════════════════════════════════════════════════════════

@router.get("/mps", response_model=dict)
async def get_mps(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Master Production Schedule — aggregate view of planned production."""
    s = date.fromisoformat(start_date) if start_date else None
    e = date.fromisoformat(end_date) if end_date else None
    return await svc.get_mps(db, s, e, status)


@router.get("/mps/gantt", response_model=dict)
async def get_mps_gantt(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Gantt chart data — operations grouped by work center."""
    s = date.fromisoformat(start_date) if start_date else None
    e = date.fromisoformat(end_date) if end_date else None
    data = await svc.get_mps_gantt_data(db, s, e)
    return {"work_centers": data, "total": len(data)}


# ═══════════════════════════════════════════════════════════════════
# ─── SHOP FLOOR CONTROL ──────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════

@router.get("/shop-floor", response_model=dict)
async def get_shop_floor(db: AsyncSession = Depends(get_db)):
    """Shop floor summary: machine utilization, WIP, active orders."""
    return await svc.get_shop_floor_summary(db)


@router.get("/shop-floor/operators", response_model=dict)
async def get_operator_workload(db: AsyncSession = Depends(get_db)):
    """Operator workload: assigned vs completed operations."""
    data = await svc.get_operator_workload(db)
    return {"operators": data, "total": len(data)}


@router.get("/shop-floor/schedule", response_model=dict)
async def get_machine_schedule(
    work_center: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Machine schedule: upcoming operations per work center."""
    data = await svc.get_machine_schedule(db, work_center)
    return {"schedule": data, "total": len(data)}
