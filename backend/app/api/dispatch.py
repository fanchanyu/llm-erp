"""Dispatch API — Production Orders, WorkCenters, Dynamic Rescheduling, CRP, APS, Gantt"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database import get_db
from app.services import dispatch_service as svc
from app.schemas.dispatch import (
    WorkCenterCreate, WorkCenterUpdate, WorkCenterResponse,
    ProductionOrderCreate, ProductionOrderUpdate, ProductionOrderResponse,
    OrderWithOperationsResponse, OperationResponse,
    DispatchRequest, DispatchResponse,
    RescheduleRequest, DispatchLogResponse,
    ScheduleRequest, BottleneckScheduleRequest,
    CrpLoadResponse, CrpLoadItem,
    GanttDataResponse, GanttOperationItem,
)

router = APIRouter()


# ═══════════════════════════════════════════════
# WorkCenter Endpoints
# ═══════════════════════════════════════════════

@router.get("/dispatch/work-centers", response_model=list[WorkCenterResponse])
async def list_work_centers(status: str = "", db: AsyncSession = Depends(get_db)):
    """列出所有工作站"""
    return await svc.list_work_centers(db, status)


@router.post("/dispatch/work-centers", response_model=WorkCenterResponse)
async def create_work_center(body: WorkCenterCreate, db: AsyncSession = Depends(get_db)):
    """新增工作站"""
    return await svc.create_work_center(db, **body.model_dump())


@router.get("/dispatch/work-centers/{wc_id}", response_model=WorkCenterResponse)
async def get_work_center(wc_id: str, db: AsyncSession = Depends(get_db)):
    """查詢工作站"""
    wc = await svc.get_work_center(db, wc_id=wc_id)
    if not wc:
        raise HTTPException(404, f"WorkCenter {wc_id} not found")
    return wc


@router.patch("/dispatch/work-centers/{wc_id}", response_model=WorkCenterResponse)
async def patch_work_center(wc_id: str, body: WorkCenterUpdate, db: AsyncSession = Depends(get_db)):
    """更新工作站（含狀態變更：idle/running/down/maintenance）"""
    wc = await svc.update_work_center(db, wc_id, **body.model_dump(exclude_none=True))
    if not wc:
        raise HTTPException(404, f"WorkCenter {wc_id} not found")
    return wc


# ═══════════════════════════════════════════════
# ProductionOrder Endpoints
# ═══════════════════════════════════════════════

@router.get("/dispatch/orders", response_model=list[OrderWithOperationsResponse])
async def list_orders(status: str = "", db: AsyncSession = Depends(get_db)):
    """列出工單（可過濾狀態）"""
    return await svc.list_orders(db, status)


@router.post("/dispatch/orders", response_model=OrderWithOperationsResponse)
async def create_order(body: ProductionOrderCreate, db: AsyncSession = Depends(get_db)):
    """建立工單"""
    order = await svc.create_order(db, **body.model_dump())
    # Reload with operations
    return await svc.get_order(db, order_id=order.id)


@router.get("/dispatch/orders/{order_no}", response_model=OrderWithOperationsResponse)
async def get_order(order_no: str, db: AsyncSession = Depends(get_db)):
    """查詢工單（含工序）"""
    order = await svc.get_order(db, order_no=order_no)
    if not order:
        raise HTTPException(404, f"Order {order_no} not found")
    return order


@router.patch("/dispatch/orders/{order_no}", response_model=OrderWithOperationsResponse)
async def patch_order(order_no: str, body: ProductionOrderUpdate, db: AsyncSession = Depends(get_db)):
    """更新工單狀態（release / complete / cancel）"""
    order = await svc.update_order(db, order_no, **body.model_dump(exclude_none=True))
    if not order:
        raise HTTPException(404, f"Order {order_no} not found")
    return await svc.get_order(db, order_id=order.id)


# ═══════════════════════════════════════════════
# Operation Endpoints
# ═══════════════════════════════════════════════

@router.post("/dispatch/orders/{order_no}/operations", response_model=OperationResponse)
async def add_operation(
    order_no: str,
    body: dict,
    db: AsyncSession = Depends(get_db),
):
    """新增工序到工單"""
    order = await svc.get_order(db, order_no=order_no)
    if not order:
        raise HTTPException(404, f"Order {order_no} not found")

    wc = await svc.get_work_center(db, name=body.get("work_center_name", ""))
    if not wc:
        raise HTTPException(404, f"WorkCenter '{body.get('work_center_name')}' not found")

    op = await svc.add_operation(
        db,
        order_id=order.id,
        work_center_id=wc.id,
        sequence_no=body["sequence_no"],
        name=body.get("name", ""),
        setup_time_min=body.get("setup_time_min", 0),
        cycle_time_min=body.get("cycle_time_min", 0),
        quantity=order.quantity,
    )
    return {
        "id": op.id,
        "order_id": op.order_id,
        "work_center_id": op.work_center_id,
        "work_center_name": wc.name,
        "sequence_no": op.sequence_no,
        "name": op.name,
        "setup_time_min": op.setup_time_min,
        "cycle_time_min": op.cycle_time_min,
        "total_time_min": op.total_time_min,
        "status": op.status,
        "scheduled_start": op.scheduled_start,
        "scheduled_end": op.scheduled_end,
        "actual_start": op.actual_start,
        "actual_end": op.actual_end,
        "delay_minutes": op.delay_minutes,
    }


# ═══════════════════════════════════════════════
# Dispatch & Reschedule
# ═══════════════════════════════════════════════

@router.post("/dispatch/dispatch", response_model=DispatchResponse)
async def dispatch(body: DispatchRequest, db: AsyncSession = Depends(get_db)):
    """派工 — 將已釋出的工單分配到工作站"""
    result = await svc.dispatch_order(db, body.order_no, body.dispatched_by, body.notes)
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@router.post("/dispatch/reschedule", response_model=dict)
async def reschedule(body: RescheduleRequest, db: AsyncSession = Depends(get_db)):
    """動態重排程 — right_shift / route_change / expedite"""
    if body.strategy == "right_shift":
        if not body.work_center_name:
            raise HTTPException(400, "work_center_name required for right_shift")
        result = await svc.right_shift_reschedule(db, body.work_center_name, 30, body.reason)
    elif body.strategy == "route_change":
        if not body.work_center_name:
            raise HTTPException(400, "work_center_name required for route_change")
        result = await svc.route_change_reschedule(db, body.work_center_name, body.reason)
    elif body.strategy == "expedite":
        if not body.order_no:
            raise HTTPException(400, "order_no required for expedite")
        result = await svc.expedite_reschedule(db, body.order_no, body.reason)
    else:
        raise HTTPException(400, f"Unknown strategy: {body.strategy}")

    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


# ═══════════════════════════════════════════════
# Dispatch Logs
# ═══════════════════════════════════════════════

@router.get("/dispatch/logs", response_model=list[dict])
async def dispatch_logs(db: AsyncSession = Depends(get_db)):
    """派工記錄"""
    return await svc.list_dispatch_logs(db)


# ═══════════════════════════════════════════════
# CRP — Capacity Requirements Planning (產能負載)
# ═══════════════════════════════════════════════

@router.get("/dispatch/crp-load", response_model=CrpLoadResponse)
async def crp_load(
    period: str = Query("day", description="Aggregation period: 'day' or 'week'"),
    db: AsyncSession = Depends(get_db),
):
    """計算工作中心產能負載 (CRP)"""
    result = await svc.calculate_crp_load(db, period)
    return result


# ═══════════════════════════════════════════════
# APS — Advanced Planning & Scheduling
# ═══════════════════════════════════════════════

@router.post("/dispatch/schedule/forward", response_model=dict)
async def schedule_forward(
    body: ScheduleRequest,
    db: AsyncSession = Depends(get_db),
):
    """前向排程 — 從今天開始，依工序順序排程"""
    result = await svc.forward_schedule(db, body.order_id)
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@router.post("/dispatch/schedule/backward", response_model=dict)
async def schedule_backward(
    body: ScheduleRequest,
    db: AsyncSession = Depends(get_db),
):
    """後向排程 — 從交期往回排"""
    result = await svc.backward_schedule(db, body.order_id)
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@router.post("/dispatch/schedule/bottleneck", response_model=dict)
async def schedule_bottleneck(
    body: BottleneckScheduleRequest,
    db: AsyncSession = Depends(get_db),
):
    """瓶頸基礎排程 (TOC) — 找出瓶頸工作站，前後分別排程"""
    result = await svc.bottleneck_schedule(db, body.order_ids)
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


# ═══════════════════════════════════════════════
# Gantt Chart Data (甘特圖數據)
# ═══════════════════════════════════════════════

@router.get("/dispatch/gantt-data", response_model=GanttDataResponse)
async def gantt_chart_data(db: AsyncSession = Depends(get_db)):
    """回傳甘特圖渲染所需完整數據"""
    return await svc.gantt_data(db)
