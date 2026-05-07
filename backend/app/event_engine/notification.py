"""Notification dispatcher — routes events to in-app and external channels.

When a DomainEvent is emitted, the notification service:
1. Resolves which roles should be notified (from role_config)
2. Creates a human-readable notification message with LLM enrichment
3. Pushes to in-app notification table (SSE/WebSocket)
4. Optionally pushes to Telegram, email, or LINE
"""
from __future__ import annotations
import json
import logging
from datetime import datetime
from typing import Optional
from .events import DomainEvent, EventSeverity
from .event_bus import get_bus
from .role_config import get_notified_roles, Role

logger = logging.getLogger(__name__)

# In-memory notification store (replace with DB in production)
_notifications: list[dict] = []
_max_keep = 500


def format_notification(event: DomainEvent) -> dict:
    """Convert a DomainEvent into a human-readable notification."""
    icon = {
        EventSeverity.CRITICAL: "🔴",
        EventSeverity.WARNING: "🟡",
        EventSeverity.INFO: "🟢",
    }.get(event.severity, "🔵")

    payload = event.payload
    summary = f"{icon} [{event.event_type}] {_summarize(event)}"

    return {
        "id": f"{event.event_type}-{event.timestamp.timestamp()}",
        "event_type": event.event_type,
        "severity": event.severity.value,
        "summary": summary,
        "actor_role": event.actor_role,
        "aggregate_id": event.aggregate_id,
        "aggregate_type": event.aggregate_type,
        "payload": payload,
        "timestamp": event.timestamp.isoformat(),
        "read": False,
    }


def _summarize(event: DomainEvent) -> str:
    p = event.payload
    t = event.event_type
    if t == "material.received":
        return f"{p.get('item','')} x{p.get('quantity','?')} 已入庫，價值 NT${p.get('value',0):,.0f}"
    if t == "material.issued":
        base = f"{p.get('item','')} x{p.get('quantity','?')} 已投料至 {event.aggregate_id}"
        if p.get("over_issue"):
            base += f" ⚠️ 超發 {p.get('excess',0)}（BOM {p.get('bom_quantity',0)}）"
        return base
    if t == "purchase_order.created":
        return f"PO {event.aggregate_id} — {p.get('supplier','')} NT${p.get('amount',0):,.0f}"
    if t == "non_conformance.created":
        return f"NC {event.aggregate_id} — {p.get('item','')} {p.get('defect','')} [{p.get('severity','')}]"
    if t == "payment.due":
        return f"應付到期 — {p.get('supplier','')} NT${p.get('amount',0):,.0f}（到期日 {p.get('due_date','')}）"
    if t == "receivable.overdue":
        return f"應收逾期 — {p.get('customer','')} NT${p.get('amount',0):,.0f}（逾期{p.get('days_overdue',0)}天）"
    # fallback
    return json.dumps(p, ensure_ascii=False)


# ─── In-App Notification Store ───────────────────────────────────

def store_notification(event: DomainEvent) -> dict:
    """Store notification in-memory and return it."""
    notif = format_notification(event)
    _notifications.append(notif)
    # Trim old entries
    while len(_notifications) > _max_keep:
        _notifications.pop(0)
    return notif


def get_notifications(role: Optional[str] = None,
                      severity: Optional[str] = None,
                      limit: int = 50) -> list[dict]:
    """Get stored notifications, optionally filtered by role and severity."""
    results = list(_notifications)
    if severity:
        results = [n for n in results if n["severity"] == severity]
    if role:
        # Filter by events that this role should see
        from .role_config import get_notified_roles, get_role_from_string
        try:
            r = get_role_from_string(role)
            valid_events = set()
            for et, roles in get_notified_roles.__wrapped__.__defaults__[0].items() if hasattr(get_notified_roles, '__wrapped__') else [].items():
                pass  # simplified — we import the dict directly
            from .role_config import EVENT_NOTIFICATION_MAP
            valid_events = {et for et, roles in EVENT_NOTIFICATION_MAP.items() if r in roles}
            results = [n for n in results if n["event_type"] in valid_events]
        except ValueError:
            pass  # no filter
    return results[-limit:]


def mark_read(notif_id: str) -> bool:
    for n in _notifications:
        if n["id"] == notif_id:
            n["read"] = True
            return True
    return False


def count_unread(role: Optional[str] = None) -> int:
    notifs = get_notifications(role=role) if role else _notifications
    return sum(1 for n in notifs if not n["read"])


# ─── Event Bus Wiring ───────────────────────────────────────────

def _on_event(event: DomainEvent):
    """Global event handler — stores notification and dispatches."""
    notif = store_notification(event)
    # Resolve target roles
    targets = get_notified_roles(event.event_type)
    # TODO: Push to Telegram/WebSocket per role channel
    logger.info(
        "Event %s | targets=%s | %s",
        event.event_type,
        [t.value for t in targets],
        notif["summary"],
    )


def init_notification_system():
    """Call once at app startup to wire event bus to notification system."""
    bus = get_bus()
    bus.subscribe_all(_on_event)
    logger.info("Notification system initialized — listening to all domain events")
