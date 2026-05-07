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
