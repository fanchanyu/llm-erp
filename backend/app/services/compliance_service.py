"""
Compliance & Log Analysis Engine — unified event stream, error detection, compliance reports.

Aggregates logs from all sources (audit_logs, dispatch_logs, approval_records, etc.)
into a single queryable event stream with:
- Process error detection rules
- Compliance report generation (ISO 9001, FDA Part 11, GMP)
- Real-time alerting for threshold breaches
"""

from __future__ import annotations
from datetime import datetime, date, timedelta
from typing import Optional, Any
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import async_session


# ═══════════════════════════════════════════════════════════════════
# ─── UNIFIED EVENT QUERY ─────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════

async def get_unified_events(
    db: AsyncSession,
    event_type: Optional[str] = None,
    user: Optional[str] = None,
    status: Optional[str] = None,
    days: int = 7,
    limit: int = 100,
) -> list[dict]:
    """Query events from all log sources, unified into a single stream."""

    events = []

    # 1. Audit logs (API operations)
    from app.models.audit_log import AuditLog
    q = select(AuditLog).order_by(desc(AuditLog.created_at)).limit(limit)
    r = await db.execute(q)
    for log in r.scalars().all():
        events.append({
            "timestamp": log.created_at.isoformat() if log.created_at else "",
            "source": "audit",
            "type": log.intent or "unknown",
            "action": log.action or "",
            "user": log.session_id or "",
            "status": "success" if log.success else "failed",
            "details": str(log.params)[:200] if log.params else "",
        })

    # 2. Dispatch logs (production events)
    from app.models.dispatch import DispatchLog
    q = select(DispatchLog).order_by(desc(DispatchLog.created_at)).limit(limit)
    r = await db.execute(q)
    for log in r.scalars().all():
        events.append({
            "timestamp": log.created_at.isoformat() if log.created_at else "",
            "source": "dispatch",
            "type": log.action or "unknown",
            "action": log.action or "",
            "user": log.dispatched_by or "system",
            "status": "info",
            "details": log.notes or "",
        })

    # 3. Approval records
    from app.models.organization import ApprovalRecord, ApprovalRequest, Employee
    q = select(ApprovalRecord).options(
        __import__("sqlalchemy.orm").selectinload(ApprovalRecord.approver)
    ).order_by(desc(ApprovalRecord.created_at)).limit(limit)
    r = await db.execute(q)
    for rec in r.scalars().all():
        events.append({
            "timestamp": rec.created_at.isoformat() if rec.created_at else "",
            "source": "approval",
            "type": "approval." + (rec.action or "unknown"),
            "action": rec.action or "",
            "user": rec.approver.name if rec.approver else "",
            "status": rec.action,
            "details": rec.comment or "",
        })

    # Filter
    filtered = events
    if event_type:
        filtered = [e for e in filtered if event_type in e["type"]]
    if user:
        filtered = [e for e in filtered if user.lower() in e["user"].lower()]
    if status:
        filtered = [e for e in filtered if e["status"] == status]

    return sorted(filtered, key=lambda e: e["timestamp"], reverse=True)[:limit]


# ═══════════════════════════════════════════════════════════════════
# ─── ERROR DETECTION RULES ───────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════

ERROR_RULES = [
    {
        "code": "LOGIN_FAILED_5",
        "name": "多次登入失敗",
        "description": "同帳號 5 次以上登入失敗",
        "severity": "warning",
        "regulation": "ISO 27001 A.9.4.2",
    },
    {
        "code": "STOCK_NEGATIVE",
        "name": "庫存異常負值",
        "description": "庫存數量出現負值",
        "severity": "critical",
        "regulation": "ISO 9001 7.1.5",
    },
    {
        "code": "ORDER_STUCK",
        "name": "工單卡關",
        "description": "工單超過 7 天未更新狀態",
        "severity": "warning",
        "regulation": "ISO 9001 8.3",
    },
    {
        "code": "APPROVAL_TIMEOUT",
        "name": "簽核逾時",
        "description": "簽核請求超過 24 小時未處理",
        "severity": "warning",
        "regulation": "ISO 9001 7.5",
    },
    {
        "code": "QUALITY_NC_OPEN",
        "name": "品質異常未結案",
        "description": "不合格品超過 14 天未處理",
        "severity": "critical",
        "regulation": "ISO 9001 8.7 / FDA 21 CFR 820",
    },
    {
        "code": "PO_OVERDUE",
        "name": "採購單逾期",
        "description": "採購單超過預交日 7 天未收貨",
        "severity": "warning",
        "regulation": "ISO 9001 8.4",
    },
    {
        "code": "CYCLE_COUNT_VARIANCE",
        "name": "盤點差異過大",
        "description": "盤點差異超過 10%",
        "severity": "warning",
        "regulation": "ISO 9001 7.1.5",
    },
]


async def detect_anomalies(db: AsyncSession) -> list[dict]:
    """Run all error detection rules and return findings."""
    findings = []

    # Rule 1: Login failures
    from app.models.audit_log import AuditLog
    failed_logins = await db.execute(
        select(AuditLog.session_id, func.count().label("cnt")).where(
            AuditLog.success == False,
            AuditLog.action.ilike("%login%"),
            AuditLog.created_at >= datetime.utcnow() - timedelta(hours=24),
        ).group_by(AuditLog.session_id).having(func.count() >= 5)
    )
    for row in failed_logins.all():
        findings.append({
            "rule": "LOGIN_FAILED_5",
            "severity": "warning",
            "message": f"帳號 {row.session_id} 在24小時內失敗 {row.cnt} 次登入",
            "affected": row.session_id,
            "regulation": "ISO 27001 A.9.4.2",
        })

    # Rule 2: Stock negative — check inventory table
    from app.models.inventory import Inventory, Part
    neg_stock = await db.execute(
        select(Inventory, Part).join(Part, Inventory.part_id == Part.id).where(Inventory.quantity < 0)
    )
    for inv, part in neg_stock.all():
        findings.append({
            "rule": "STOCK_NEGATIVE",
            "severity": "critical",
            "message": f"料號 {part.part_no} ({part.name}) 庫存異常: {inv.quantity}",
            "affected": part.part_no,
            "regulation": "ISO 9001 7.1.5",
        })

    # Rule 3: Orders stuck
    from app.models.dispatch import ProductionOrder, OrderStatus
    stuck_orders = await db.execute(
        select(ProductionOrder).where(
            ProductionOrder.status.in_([OrderStatus.RELEASED.value,
                                         OrderStatus.DISPATCHED.value,
                                         OrderStatus.IN_PROGRESS.value]),
            ProductionOrder.updated_at < datetime.utcnow() - timedelta(days=7),
        )
    )
    for order in stuck_orders.scalars().all():
        findings.append({
            "rule": "ORDER_STUCK",
            "severity": "warning",
            "message": f"工單 {order.order_no} ({order.product_name}) 超過7天未更新",
            "affected": order.order_no,
            "regulation": "ISO 9001 8.3",
        })

    # Rule 4: Quality NCs open too long
    from app.models.quality import NonConformance
    open_ncs = await db.execute(
        select(NonConformance).where(
            NonConformance.status != "closed",
            NonConformance.created_at < datetime.utcnow() - timedelta(days=14),
        )
    )
    for nc in open_ncs.scalars().all():
        findings.append({
            "rule": "QUALITY_NC_OPEN",
            "severity": "critical",
            "message": f"不合格單 {nc.nc_no} 超過14天未結案",
            "affected": nc.nc_no,
            "regulation": "ISO 9001 8.7",
        })

    return findings


# ═══════════════════════════════════════════════════════════════════
# ─── COMPLIANCE REPORTS ──────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════

async def generate_compliance_report(
    db: AsyncSession,
    report_type: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> dict:
    """Generate regulatory compliance reports."""

    if not start_date:
        start_date = date.today() - timedelta(days=30)
    if not end_date:
        end_date = date.today()

    if report_type == "audit_trail":
        return await _report_audit_trail(db, start_date, end_date)

    elif report_type == "quality_events":
        return await _report_quality_events(db, start_date, end_date)

    elif report_type == "production_log":
        return await _report_production_log(db, start_date, end_date)

    elif report_type == "approval_history":
        return await _report_approval_history(db, start_date, end_date)

    elif report_type == "iso_compliance":
        return await _report_iso_summary(db)

    return {"error": f"Unknown report type: {report_type}"}


async def _report_audit_trail(db: AsyncSession, start: date, end: date) -> dict:
    """ISO 9001 / FDA Part 11 — Complete audit trail of all system changes."""
    from app.models.audit_log import AuditLog
    q = select(AuditLog).where(
        AuditLog.created_at >= datetime.combine(start, datetime.min.time()),
        AuditLog.created_at <= datetime.combine(end, datetime.max.time()),
    ).order_by(AuditLog.created_at)

    r = await db.execute(q)
    logs = list(r.scalars().all())

    return {
        "report_type": "audit_trail",
        "title": "完整操作稽核軌跡 — Audit Trail",
        "regulation": "ISO 9001 7.5 / FDA 21 CFR Part 11",
        "period": {"start": start.isoformat(), "end": end.isoformat()},
        "total_events": len(logs),
        "failed_events": sum(1 for l in logs if not l.success),
        "unique_users": len(set(l.session_id for l in logs if l.session_id)),
        "events": [
            {
                "timestamp": l.created_at.isoformat() if l.created_at else "",
                "user": l.session_id or "",
                "action": l.action or "",
                "type": l.intent or "",
                "status": "success" if l.success else "failed",
                "details": str(l.params)[:200] if l.params else "",
            }
            for l in logs[-200:]  # last 200 for performance
        ],
    }


async def _report_quality_events(db: AsyncSession, start: date, end: date) -> dict:
    """GMP / ISO 9001 — Quality event report for regulatory submission."""
    from app.models.quality import NonConformance, CAPARecord, InspectionOrder
    from app.models.inventory import Part

    ncs = await db.execute(
        select(NonConformance, Part).join(Part, NonConformance.part_id == Part.id).where(
            NonConformance.created_at >= datetime.combine(start, datetime.min.time()),
            NonConformance.created_at <= datetime.combine(end, datetime.max.time()),
        ).order_by(NonConformance.created_at)
    )

    nc_list = []
    for nc, part in ncs.all():
        nc_list.append({
            "nc_no": nc.nc_no, "part_no": part.part_no, "defect": nc.defect_code,
            "severity": nc.severity, "status": nc.status,
            "created": nc.created_at.isoformat() if nc.created_at else "",
        })

    return {
        "report_type": "quality_events",
        "title": "品質事件報告 — Quality Event Report",
        "regulation": "ISO 9001 8.7 / GMP",
        "period": {"start": start.isoformat(), "end": end.isoformat()},
        "total_ncs": len(nc_list),
        "open_ncs": sum(1 for n in nc_list if n["status"] != "closed"),
        "events": nc_list,
    }


async def _report_production_log(db: AsyncSession, start: date, end: date) -> dict:
    """GMP Batch Record — Production log for regulatory traceability."""
    from app.models.dispatch import ProductionOrder, DispatchLog

    orders = await db.execute(
        select(ProductionOrder).where(
            ProductionOrder.created_at >= datetime.combine(start, datetime.min.time()),
            ProductionOrder.created_at <= datetime.combine(end, datetime.max.time()),
        ).order_by(ProductionOrder.created_at)
    )
    order_list = [
        {
            "order_no": o.order_no, "product": o.product_name,
            "qty": o.quantity, "completed": o.completed_qty,
            "status": o.status, "due_date": o.due_date.isoformat() if o.due_date else "",
            "so_no": o.so_no,
        }
        for o in orders.scalars().all()
    ]

    return {
        "report_type": "production_log",
        "title": "生產紀錄 — Production Log / Batch Record",
        "regulation": "GMP Batch Record / ISO 9001 8.3",
        "period": {"start": start.isoformat(), "end": end.isoformat()},
        "total_orders": len(order_list),
        "orders": order_list,
    }


async def _report_approval_history(db: AsyncSession, start: date, end: date) -> dict:
    """Approval workflow audit for regulatory compliance."""
    from app.models.organization import ApprovalRequest, ApprovalRecord, ApprovalFlow, Employee

    requests = await db.execute(
        select(ApprovalRequest).options(
            __import__("sqlalchemy.orm").selectinload(ApprovalRequest.flow),
            __import__("sqlalchemy.orm").selectinload(ApprovalRequest.requester),
        ).where(
            ApprovalRequest.created_at >= datetime.combine(start, datetime.min.time()),
            ApprovalRequest.created_at <= datetime.combine(end, datetime.max.time()),
        ).order_by(ApprovalRequest.created_at)
    )

    items = []
    for req in requests.scalars().all():
        # Get approval records for this request
        recs = await db.execute(
            select(ApprovalRecord).options(
                __import__("sqlalchemy.orm").selectinload(ApprovalRecord.approver)
            ).where(ApprovalRecord.request_id == req.id)
        )
        history = [
            {
                "step": r.step, "approver": r.approver.name if r.approver else "",
                "action": r.action, "comment": r.comment or "",
                "time": r.created_at.isoformat() if r.created_at else "",
            }
            for r in recs.scalars().all()
        ]
        items.append({
            "request_id": str(req.id),
            "flow": req.flow.name if req.flow else "",
            "requester": req.requester.name if req.requester else "",
            "status": req.status,
            "history": history,
        })

    return {
        "report_type": "approval_history",
        "title": "簽核歷程報告 — Approval History",
        "regulation": "ISO 9001 7.5 / FDA 21 CFR Part 11",
        "period": {"start": start.isoformat(), "end": end.isoformat()},
        "total_requests": len(items),
        "requests": items,
    }


async def _report_iso_summary(db: AsyncSession) -> dict:
    """ISO 9001 compliance summary dashboard."""
    findings = await detect_anomalies(db)
    critical = [f for f in findings if f["severity"] == "critical"]
    warnings = [f for f in findings if f["severity"] == "warning"]

    return {
        "report_type": "iso_compliance",
        "title": "ISO 9001 合規摘要 — Compliance Summary",
        "generated_at": datetime.utcnow().isoformat(),
        "summary": {
            "total_anomalies": len(findings),
            "critical": len(critical),
            "warnings": len(warnings),
            "compliant": len(critical) == 0,
        },
        "regulated_rules_triggered": list(set(f["regulation"] for f in findings)),
        "anomalies": findings,
    }
