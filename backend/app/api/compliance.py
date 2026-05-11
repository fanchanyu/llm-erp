"""Compliance & Log Analysis API — event stream, anomaly detection, compliance reports."""

from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.services import compliance_service as svc
from app.models.organization import ApprovalRecord, ApprovalRequest, Employee
from app.models.audit_log import AuditLog
from app.models.dispatch import DispatchLog

router = APIRouter(prefix="/compliance", tags=["compliance"])


@router.get("/events", response_model=dict)
async def get_events(
    event_type: Optional[str] = Query(None),
    user: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    days: int = Query(7),
    limit: int = Query(100),
    db: AsyncSession = Depends(get_db),
):
    """Unified event stream — combines audit, dispatch, and approval logs."""
    events = await svc.get_unified_events(db, event_type, user, status, days, limit)
    return {"events": events, "total": len(events)}


@router.get("/anomalies", response_model=dict)
async def get_anomalies(db: AsyncSession = Depends(get_db)):
    """Run error detection rules and return findings."""
    findings = await svc.detect_anomalies(db)
    return {
        "anomalies": findings,
        "total": len(findings),
        "critical": len([f for f in findings if f["severity"] == "critical"]),
        "warnings": len([f for f in findings if f["severity"] == "warning"]),
    }


@router.get("/reports/{report_type}", response_model=dict)
async def get_compliance_report(
    report_type: str,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Generate compliance reports.
    
    Report types:
    - audit_trail: ISO 9001 / FDA Part 11 audit trail
    - quality_events: GMP quality event report
    - production_log: GMP batch record
    - approval_history: Approval workflow audit
    - iso_compliance: ISO 9001 compliance summary
    """
    start = date.fromisoformat(start_date) if start_date else None
    end = date.fromisoformat(end_date) if end_date else None
    report = await svc.generate_compliance_report(db, report_type, start, end)
    return report


@router.get("/regulated-rules", response_model=dict)
async def get_regulated_rules():
    """List all monitored compliance rules with their regulatory references."""
    rules = [
        {
            "code": r["code"],
            "name": r["name"],
            "description": r["description"],
            "severity": r["severity"],
            "regulation": r["regulation"],
        }
        for r in svc.ERROR_RULES
    ]
    return {"rules": rules, "total": len(rules)}
