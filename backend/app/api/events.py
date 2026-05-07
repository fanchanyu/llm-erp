"""Event engine API endpoints.

Provides REST endpoints for:
- Notifications (in-app notification center)
- Events (event flow feed for the dashboard)
- Constraint checking (proactive validation)
"""
from fastapi import APIRouter, Query
from pydantic import BaseModel
from app.event_engine import (
    get_notifications, count_unread, mark_read,
    get_checker,
)
from app.event_engine.events import (
    material_issued, material_received, po_created, nc_created,
)
from app.event_engine.event_bus import get_bus

router = APIRouter(prefix="/events", tags=["events"])


class ConstraintRequest(BaseModel):
    operation: str
    params: dict = {}
    actor_role: str = ""


@router.post("/check")
async def check_constraints(req: ConstraintRequest):
    """Run constraint checks for an operation before execution.

    Returns list of BLOCK, WARN, PASS verdicts.
    The caller should NOT proceed if any result is BLOCK.
    """
    checker = get_checker()
    verdicts = checker.check(req.operation, req.params, req.actor_role)
    return {
        "operation": req.operation,
        "verdicts": [
            {
                "result": v.result.value,
                "code": v.code,
                "message": v.message,
                "details": v.details,
                "alternatives": v.alternatives,
                "required_approval_role": v.required_approval_role,
                "affected_entities": v.affected_entities,
            }
            for v in verdicts
        ],
        "summary": checker.summary(verdicts),
    }


@router.get("/notifications")
async def list_notifications(
    role: str = Query(None, description="Filter by role"),
    severity: str = Query(None, description="Filter by severity"),
    limit: int = Query(50, ge=1, le=200),
):
    """Get notifications, optionally filtered by role and severity."""
    notifs = get_notifications(role=role, severity=severity, limit=limit)
    unread = count_unread(role=role)
    return {"notifications": notifs, "unread_count": unread, "total": len(notifs)}


@router.get("/notifications/unread")
async def unread_count(role: str = Query(None)):
    """Get unread notification count (for badge display)."""
    return {"unread": count_unread(role=role)}


@router.post("/notifications/{notif_id}/read")
async def read_notification(notif_id: str):
    """Mark a notification as read."""
    ok = mark_read(notif_id)
    return {"ok": ok}


@router.get("/activity")
async def recent_activity(limit: int = Query(10, ge=1, le=50)):
    """Get recent event activity flow (for dashboard event-flow widget)."""
    notifs = get_notifications(limit=limit)
    # Reverse to show newest first
    return {"events": list(reversed(notifs))}


@router.post("/simulate/{event_type}")
async def simulate_event(event_type: str):
    """Emit a sample event for testing/demo purposes."""
    bus = get_bus()
    if event_type == "material.received":
        ev = material_received("PO-DEMO-001", "鋁板6061", 500, 85000)
    elif event_type == "material.issued":
        ev = material_issued("WO-DEMO-001", "底板", 100, 80)
    elif event_type == "purchase_order.created":
        ev = po_created("PO-DEMO-002", "大明金屬", 120000)
    elif event_type == "non_conformance.created":
        ev = nc_created("NC-DEMO-001", "ASM-001", "尺寸超差", "major")
    else:
        return {"error": f"Unknown event type: {event_type}"}, 400
    bus.emit(ev)
    return {
        "emitted": event_type,
        "actor_role": ev.actor_role,
        "aggregate_id": ev.aggregate_id,
        "severity": ev.severity.value,
    }
