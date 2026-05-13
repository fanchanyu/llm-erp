"""War Room — 整合戰情室 API
提供單一端點，一次性回傳所有節點的 KPI 與健康狀態。
"""
from datetime import datetime, date
from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.models.dispatch import ProductionOrder, OrderStatus
from app.models.inventory import Part, Inventory
from app.models.purchase import Supplier, PurchaseOrder, PurchaseOrderItem
from app.models.quality import NonConformance
from app.models.organization import Department, ApprovalRequest
from app.models.accounting import AccountsReceivable
from app.models.bom import Product

router = APIRouter(prefix="/war-room", tags=["war-room"])


@router.get("/summary")
async def war_room_summary(db: AsyncSession = Depends(get_db)):
    """單一 API 回傳戰情室全部節點 KPI + 健康狀態"""
    now = datetime.now()

    # ── 1. 組織 (Phase 0) ──
    dept_count = (await db.execute(select(func.count()).select_from(Department))).scalar() or 0
    pending_approvals = (await db.execute(
        select(func.count()).select_from(ApprovalRequest).where(ApprovalRequest.status == "pending")
    )).scalar() or 0
    org_status = "warning" if pending_approvals > 0 else "healthy"

    # ── 2. CRM ──
    total_leads = 0
    try:
        total_leads = (await db.execute(select(func.count()).select_from(
            type("T", (), {"__tablename__": "leads"})()
        ))).scalar() or 0
    except:
        pass

    # ── 3. MPS ──
    mps_count = 0
    try:
        mps_count = (await db.execute(select(func.count()).select_from(
            type("T", (), {"__tablename__": "mps_entries"})()
        ))).scalar() or 0
    except:
        pass

    # ── 4. MRP ──
    mrp_count = 0
    try:
        mrp_count = (await db.execute(select(func.count()).select_from(
            type("T", (), {"__tablename__": "mrp_items"})()
        ))).scalar() or 0
    except:
        pass

    # ── 5. CRP/APS ──
    total_wo = (await db.execute(select(func.count()).select_from(ProductionOrder))).scalar() or 0
    active_wo = (await db.execute(
        select(func.count()).select_from(ProductionOrder)
        .where(ProductionOrder.status.in_(["released", "dispatched", "in_progress"]))
    )).scalar() or 0
    overdue_wo = (await db.execute(
        select(func.count()).select_from(ProductionOrder)
        .where(
            ProductionOrder.status.in_(["released", "dispatched", "in_progress"]),
            ProductionOrder.due_date < now.date()
        )
    )).scalar() or 0
    crp_utilization = min(100.0, round((active_wo / max(total_wo, 1)) * 100, 1))

    # ── 6. 派工 (SFC) ──
    dispatch_status = "healthy"
    if overdue_wo > 0:
        dispatch_status = "critical" if overdue_wo > 2 else "warning"

    # ── 7. 品管 ──
    open_ncs = (await db.execute(
        select(func.count()).select_from(NonConformance)
        .where(NonConformance.status != "closed")
    )).scalar() or 0
    quality_status = "healthy" if open_ncs == 0 else "critical" if open_ncs > 3 else "warning"

    # ── 8. 倉儲 ──
    stock_count = (await db.execute(
        select(func.count()).select_from(Inventory)
        .where(Inventory.quantity > 0)
    )).scalar() or 0
    # Low stock: quantity > 0 but below some threshold (use 20 as default)
    low_stock = (await db.execute(
        select(func.count()).select_from(Inventory)
        .where(and_(Inventory.quantity > 0, Inventory.quantity < 20))
    )).scalar() or 0
    stock_status = "warning" if low_stock > 0 else "healthy"

    # ── 9. 供應商 ──
    supplier_count = (await db.execute(select(func.count()).select_from(Supplier))).scalar() or 0
    try:
        avg_score = (await db.execute(
            select(func.avg(Supplier.score)).where(Supplier.score.isnot(None))
        )).scalar() or 0.0
    except:
        avg_score = 0.0
    supplier_status = "warning" if avg_score and avg_score < 3.0 else "healthy"

    # ── 10. 財務 ──
    ar_items = (await db.execute(
        select(AccountsReceivable).order_by(AccountsReceivable.due_date)
    )).scalars().all()
    ar_count = len(ar_items)
    ar_total = sum(float(a.amount) for a in ar_items)
    ar_overdue = sum(float(a.amount) for a in ar_items if a.due_date and a.due_date < now.date())
    ar_status = "critical" if ar_overdue > 1000000 else ("warning" if ar_overdue > 0 else "healthy")

    return {
        "timestamp": now.isoformat(),
        "nodes": {
            "organization": {
                "label": "組織",
                "icon": "🏛️",
                "kpi": f"{pending_approvals} 待簽核",
                "detail": f"{dept_count} 部門",
                "status": org_status,
            },
            "crm": {
                "label": "CRM",
                "icon": "🤝",
                "kpi": f"{total_leads} 商機",
                "detail": f"本月",
                "status": "healthy",
            },
            "mps": {
                "label": "MPS",
                "icon": "📊",
                "kpi": f"{mps_count} 計畫",
                "detail": "主排程",
                "status": "healthy",
            },
            "mrp": {
                "label": "MRP",
                "icon": "🧮",
                "kpi": f"{mrp_count} 建議",
                "detail": "物料需求",
                "status": "healthy",
            },
            "crp": {
                "label": "CRP/APS",
                "icon": "⚡",
                "kpi": f"{crp_utilization}%",
                "detail": f"{active_wo}/{total_wo} 工單",
                "status": dispatch_status,
            },
            "dispatch": {
                "label": "派工",
                "icon": "⚙️",
                "kpi": f"{active_wo} 工單",
                "detail": f"{overdue_wo} 逾期",
                "status": dispatch_status,
            },
            "quality": {
                "label": "品管",
                "icon": "✅",
                "kpi": f"{open_ncs} NC",
                "detail": "未結",
                "status": quality_status,
            },
            "inventory": {
                "label": "倉儲",
                "icon": "📦",
                "kpi": f"{stock_count} 項",
                "detail": f"{low_stock} 低庫存",
                "status": stock_status,
            },
            "suppliers": {
                "label": "供應商",
                "icon": "🏭",
                "kpi": f"{supplier_count} 家",
                "detail": f"均分 {avg_score:.1f}" if avg_score else "",
                "status": supplier_status,
            },
            "accounting": {
                "label": "財務",
                "icon": "💰",
                "kpi": f"NT${ar_total:,.0f}",
                "detail": f"{ar_overdue:,.0f} 逾期",
                "status": ar_status,
            },
        },
    }
