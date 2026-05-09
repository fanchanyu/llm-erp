"""Domain event definitions for LLM-ERP event-driven architecture.

Each event type represents a meaningful business occurrence that may
trigger cross-role notifications, constraint checks, or audit logging.
"""
from __future__ import annotations
from enum import Enum, auto
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


class EventCategory(Enum):
    """High-level category for routing and filtering."""
    MATERIAL = auto()       # inventory movements
    PRODUCTION = auto()     # work order lifecycle
    PURCHASE = auto()       # PO lifecycle
    QUALITY = auto()        # NC, inspection
    FINANCE = auto()        # payment, cost
    SYSTEM = auto()         # config, user management


class EventSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class DomainEvent:
    """Base class for all domain events."""
    event_type: str
    category: EventCategory
    severity: EventSeverity = EventSeverity.INFO
    actor_role: str = ""
    actor_id: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    aggregate_id: str = ""         # e.g. PO number, WO number
    aggregate_type: str = ""       # e.g. "purchase_order", "work_order"
    payload: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)


# ─── Concrete Event Helpers ───────────────────────────────────────

def material_received(po_ref: str, item: str, qty: float, value: float,
                      actor_role: str = "warehouse") -> DomainEvent:
    return DomainEvent(
        event_type="material.received",
        category=EventCategory.MATERIAL,
        actor_role=actor_role,
        aggregate_id=po_ref,
        aggregate_type="purchase_order",
        payload={"item": item, "quantity": qty, "value": value},
        metadata={"notification_targets": ["purchasing", "quality", "accounting"]},
    )


def material_issued(wo_ref: str, item: str, qty: float,
                    bom_qty: float, actor_role: str = "production") -> DomainEvent:
    over_issue = qty > bom_qty
    return DomainEvent(
        event_type="material.issued",
        category=EventCategory.MATERIAL,
        severity=EventSeverity.WARNING if over_issue else EventSeverity.INFO,
        actor_role=actor_role,
        aggregate_id=wo_ref,
        aggregate_type="work_order",
        payload={"item": item, "quantity": qty, "bom_quantity": bom_qty,
                 "over_issue": over_issue, "excess": qty - bom_qty if over_issue else 0},
        metadata={"notification_targets": ["warehouse", "accounting", "director"]}
        if over_issue else {"notification_targets": ["warehouse", "accounting"]},
    )


def po_created(po_ref: str, supplier: str, amount: float,
               actor_role: str = "purchasing") -> DomainEvent:
    return DomainEvent(
        event_type="purchase_order.created",
        category=EventCategory.PURCHASE,
        actor_role=actor_role,
        aggregate_id=po_ref,
        aggregate_type="purchase_order",
        payload={"supplier": supplier, "amount": amount},
        metadata={"notification_targets": ["accounting", "warehouse"]},
    )


def wo_released(wo_ref: str, item: str, qty: int,
                due_date: str, actor_role: str = "production") -> DomainEvent:
    return DomainEvent(
        event_type="work_order.released",
        category=EventCategory.PRODUCTION,
        actor_role=actor_role,
        aggregate_id=wo_ref,
        aggregate_type="work_order",
        payload={"item": item, "quantity": qty, "due_date": due_date},
        metadata={"notification_targets": ["warehouse"]},
    )


def nc_created(nc_ref: str, item: str, defect: str, severity: str,
               actor_role: str = "quality") -> DomainEvent:
    sev = EventSeverity.CRITICAL if severity in ("critical", "major") else EventSeverity.WARNING
    return DomainEvent(
        event_type="non_conformance.created",
        category=EventCategory.QUALITY,
        severity=sev,
        actor_role=actor_role,
        aggregate_id=nc_ref,
        aggregate_type="non_conformance",
        payload={"item": item, "defect": defect, "severity": severity},
        metadata={"notification_targets": ["production", "director"]}
        if sev == EventSeverity.CRITICAL else {"notification_targets": ["production"]},
    )


def payment_due(supplier: str, amount: float, due_date: str,
                actor_role: str = "accounting") -> DomainEvent:
    return DomainEvent(
        event_type="payment.due",
        category=EventCategory.FINANCE,
        severity=EventSeverity.WARNING,
        actor_role=actor_role,
        aggregate_id=f"AP-{supplier}",
        aggregate_type="accounts_payable",
        payload={"supplier": supplier, "amount": amount, "due_date": due_date},
        metadata={"notification_targets": ["director", "purchasing"]},
    )


def ar_overdue(customer: str, amount: float, days_overdue: int,
               actor_role: str = "accounting") -> DomainEvent:
    sev = EventSeverity.CRITICAL if days_overdue > 30 else EventSeverity.WARNING
    return DomainEvent(
        event_type="receivable.overdue",
        category=EventCategory.FINANCE,
        severity=sev,
        actor_role=actor_role,
        aggregate_id=f"AR-{customer}",
        aggregate_type="accounts_receivable",
        payload={"customer": customer, "amount": amount, "days_overdue": days_overdue},
        metadata={"notification_targets": ["director"]}
        if sev == EventSeverity.CRITICAL else {"notification_targets": []},
    )


def cash_projected(balance: float, projected_in: float, projected_out: float,
                   days: int = 30, actor_role: str = "accounting") -> DomainEvent:
    """Cash position projected (現金水位預測)."""
    low = balance + projected_in - projected_out < balance * 0.1
    return DomainEvent(
        event_type="cash.projected",
        category=EventCategory.FINANCE,
        severity=EventSeverity.WARNING if low else EventSeverity.INFO,
        actor_role=actor_role,
        aggregate_id=f"cash-{days}d",
        aggregate_type="cash_flow",
        payload={"balance": balance, "projected_in": projected_in,
                 "projected_out": projected_out, "projected_end": balance + projected_in - projected_out,
                 "days": days, "low": low},
        metadata={"notification_targets": ["director", "purchasing"]}
        if low else {"notification_targets": ["director"]},
    )


def cash_alert_low(balance: float, min_required: float,
                   actor_role: str = "accounting") -> DomainEvent:
    """Cash below safety threshold (現金低於安全線)."""
    return DomainEvent(
        event_type="cash.alert_low",
        category=EventCategory.FINANCE,
        severity=EventSeverity.CRITICAL,
        actor_role=actor_role,
        aggregate_id="cash-alert",
        aggregate_type="cash_flow",
        payload={"balance": balance, "min_required": min_required, "shortfall": min_required - balance},
        metadata={"notification_targets": ["director", "purchasing", "production"]},
    )


def rush_order_assessed(so_ref: str, customer: str, amount: float,
                        premium: float, net_benefit: float, recommended: bool,
                        actor_role: str = "sales") -> DomainEvent:
    """Rush order financial assessment (急單財務評估)."""
    return DomainEvent(
        event_type="rush_order.assessed",
        category=EventCategory.PRODUCTION,
        severity=EventSeverity.INFO if recommended else EventSeverity.WARNING,
        actor_role=actor_role,
        aggregate_id=so_ref,
        aggregate_type="sales_order",
        payload={"customer": customer, "amount": amount, "premium": premium,
                 "net_benefit": net_benefit, "recommended": recommended},
        metadata={"notification_targets": ["director", "production", "accounting"]},
    )


def decision_made(decision_type: str, description: str, department: str,
                  actor_role: str = "") -> DomainEvent:
    """A business decision was made (部門決策紀錄)."""
    return DomainEvent(
        event_type="decision.made",
        category=EventCategory.SYSTEM,
        severity=EventSeverity.INFO,
        actor_role=actor_role or department,
        aggregate_id=f"decision-{decision_type}",
        aggregate_type="decision_log",
        payload={"decision_type": decision_type, "description": description, "department": department},
        metadata={"notification_targets": ["director"]},
    )


def aar_completed(decision_id: str, department: str, variance: str,
                  actor_role: str = "") -> DomainEvent:
    """After Action Review completed (決策回顧完成)."""
    return DomainEvent(
        event_type="decision.aar_completed",
        category=EventCategory.SYSTEM,
        severity=EventSeverity.INFO,
        actor_role=actor_role or department,
        aggregate_id=f"aar-{decision_id}",
        aggregate_type="after_action_review",
        payload={"decision_id": decision_id, "department": department, "variance_summary": variance},
        metadata={"notification_targets": ["director", department]},
    )
