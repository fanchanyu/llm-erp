"""Role configuration and permission model.

Defines the six ERP user archetypes, their widget visibility,
permission boundaries, LLM interaction modes, and notification preferences.
"""
from __future__ import annotations
from enum import Enum
from dataclasses import dataclass, field
from typing import List


class Role(Enum):
    DIRECTOR = "director"       # 廠長 — Factory Director
    PRODUCTION = "production"   # 生管 — Production Controller
    WAREHOUSE = "warehouse"     # 倉庫 — Warehouse Keeper
    PURCHASING = "purchasing"   # 採購 — Purchasing Agent
    QUALITY = "quality"         # 品管 — Quality Inspector
    ACCOUNTING = "accounting"   # 會計 — Accountant/CFO


class DecisionLevel(Enum):
    STRATEGIC = "strategic"
    TACTICAL = "tactical"
    OPERATIONAL = "operational"
    ANALYTIC = "analytic"
    PREDICTIVE = "predictive"


class LLMMode(Enum):
    STRATEGIC = "strategic"       # trend analysis, exception summary
    TACTICAL = "tactical"         # what-if simulation, multi-option
    EXECUTION = "execution"       # command-driven, scan-oriented
    ANALYTIC = "analytic"         # defect analysis, root cause
    PREDICTIVE = "predictive"     # cash forecast, recommendations


@dataclass
class RoleConfig:
    role: Role
    label: str
    label_en: str
    icon: str
    decision_level: DecisionLevel
    llm_mode: LLMMode
    widgets: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)
    notify_categories: List[str] = field(default_factory=list)

    @property
    def name(self) -> str:
        return self.role.value


# ─── Widget IDs ──────────────────────────────────────────────────
# These must match React component names on the frontend

WIDGET_ALERT = "alert-bar"
WIDGET_KPI = "kpi-grid"           # role-specific content
WIDGET_INVENTORY_CHART = "inventory-chart"
WIDGET_AI_INSIGHTS = "ai-insights"
WIDGET_QUALITY_SUMMARY = "quality-panel"
WIDGET_PO_TABLE = "po-table"
WIDGET_OVERDUE_ORDERS = "overdue-orders"
WIDGET_DISPATCH_GANTT = "dispatch-gantt"
WIDGET_PICK_LIST = "pick-list"
WIDGET_PUTAWAY_QUEUE = "putaway-queue"
WIDGET_INVENTORY_SEARCH = "inventory-search"
WIDGET_STOCK_ALERTS = "stock-alerts"
WIDGET_SUPPLIER_LIST = "supplier-list"
WIDGET_SHORTAGE_FORECAST = "shortage-forecast"
WIDGET_PRICE_TREND = "price-trend"
WIDGET_INSPECTION_QUEUE = "inspection-queue"
WIDGET_NC_LIST = "nc-list"
WIDGET_DEFECT_PARETO = "defect-pareto"
WIDGET_CAPA_TRACKER = "capa-tracker"
WIDGET_CASH_FLOW = "cash-flow"
WIDGET_AR_AGING = "ar-aging"
WIDGET_AP_AGING = "ap-aging"
WIDGET_COST_VARIANCE = "cost-variance"
WIDGET_GL_JOURNAL = "gl-journal"
WIDGET_MONTH_CLOSE = "month-close"
WIDGET_EVENT_FLOW = "event-flow"
WIDGET_CAPACITY_ADJUST = "capacity-adjust"
WIDGET_SHORTAGE_TABLE = "shortage-table"
WIDGET_PRODUCTION_INSIGHTS = "production-insights"

# ─── Role Definitions ────────────────────────────────────────────

ROLE_CONFIGS: dict[Role, RoleConfig] = {
    Role.DIRECTOR: RoleConfig(
        role=Role.DIRECTOR,
        label="廠長",
        label_en="Factory Director",
        icon="👨‍💼",
        decision_level=DecisionLevel.STRATEGIC,
        llm_mode=LLMMode.STRATEGIC,
        widgets=[
            WIDGET_ALERT, WIDGET_KPI, WIDGET_INVENTORY_CHART,
            WIDGET_AI_INSIGHTS, WIDGET_QUALITY_SUMMARY,
            WIDGET_PO_TABLE, WIDGET_OVERDUE_ORDERS, WIDGET_EVENT_FLOW,
        ],
        permissions=[
            "view-all", "approve-over-issue", "approve-po-above-100k",
            "approve-scrap", "view-financial-summary",
        ],
        notify_categories=["critical"],
    ),
    Role.PRODUCTION: RoleConfig(
        role=Role.PRODUCTION,
        label="生管",
        label_en="Production Controller",
        icon="👨‍🔧",
        decision_level=DecisionLevel.TACTICAL,
        llm_mode=LLMMode.TACTICAL,
        widgets=[
            WIDGET_ALERT, WIDGET_KPI, WIDGET_DISPATCH_GANTT,
            WIDGET_PRODUCTION_INSIGHTS, WIDGET_SHORTAGE_TABLE,
            WIDGET_OVERDUE_ORDERS, WIDGET_CAPACITY_ADJUST, WIDGET_EVENT_FLOW,
        ],
        permissions=[
            "view-production", "edit-schedule", "release-wo", "hold-wo",
            "split-wo", "reschedule",
        ],
        notify_categories=["critical", "warning"],
    ),
    Role.WAREHOUSE: RoleConfig(
        role=Role.WAREHOUSE,
        label="倉庫",
        label_en="Warehouse Keeper",
        icon="📦",
        decision_level=DecisionLevel.OPERATIONAL,
        llm_mode=LLMMode.EXECUTION,
        widgets=[
            WIDGET_PICK_LIST, WIDGET_PUTAWAY_QUEUE,
            WIDGET_INVENTORY_SEARCH, WIDGET_STOCK_ALERTS,
            WIDGET_KPI, WIDGET_EVENT_FLOW,
        ],
        permissions=[
            "view-inventory", "receive-stock", "issue-stock",
            "transfer-stock", "cycle-count", "adjust-stock",
        ],
        notify_categories=["task"],
    ),
    Role.PURCHASING: RoleConfig(
        role=Role.PURCHASING,
        label="採購",
        label_en="Purchasing Agent",
        icon="📋",
        decision_level=DecisionLevel.TACTICAL,
        llm_mode=LLMMode.TACTICAL,
        widgets=[
            WIDGET_ALERT, WIDGET_KPI, WIDGET_PO_TABLE,
            WIDGET_SUPPLIER_LIST, WIDGET_SHORTAGE_FORECAST,
            WIDGET_PRICE_TREND, WIDGET_EVENT_FLOW,
        ],
        permissions=[
            "create-po", "edit-po", "approve-po-below-100k",
            "view-suppliers", "rate-suppliers",
        ],
        notify_categories=["critical", "warning"],
    ),
    Role.QUALITY: RoleConfig(
        role=Role.QUALITY,
        label="品管",
        label_en="Quality Inspector",
        icon="✅",
        decision_level=DecisionLevel.ANALYTIC,
        llm_mode=LLMMode.ANALYTIC,
        widgets=[
            WIDGET_INSPECTION_QUEUE, WIDGET_NC_LIST,
            WIDGET_DEFECT_PARETO, WIDGET_CAPA_TRACKER,
            WIDGET_KPI, WIDGET_EVENT_FLOW,
        ],
        permissions=[
            "create-nc", "disposition-nc", "close-nc",
            "view-inspection-results", "create-capa",
        ],
        notify_categories=["critical", "warning"],
    ),
    Role.ACCOUNTING: RoleConfig(
        role=Role.ACCOUNTING,
        label="會計",
        label_en="Accountant/CFO",
        icon="💰",
        decision_level=DecisionLevel.PREDICTIVE,
        llm_mode=LLMMode.PREDICTIVE,
        widgets=[
            WIDGET_CASH_FLOW, WIDGET_AR_AGING, WIDGET_AP_AGING,
            WIDGET_COST_VARIANCE, WIDGET_GL_JOURNAL,
            WIDGET_MONTH_CLOSE, WIDGET_KPI, WIDGET_EVENT_FLOW,
        ],
        permissions=[
            "view-financial", "approve-payment", "cost-close",
            "view-gl", "view-pnl", "view-balance-sheet",
        ],
        notify_categories=["critical", "warning"],
    ),
}


def get_config(role: Role) -> RoleConfig:
    return ROLE_CONFIGS[role]


def get_role_from_string(s: str) -> Role:
    for r in Role:
        if r.value == s:
            return r
    raise ValueError(f"Unknown role: {s}")


# ─── Event-to-role notification mapping ─────────────────────────
# Which event types trigger notifications for which roles?

EVENT_NOTIFICATION_MAP: dict[str, list[Role]] = {
    "material.received":        [Role.PURCHASING, Role.QUALITY, Role.ACCOUNTING],
    "material.issued":          [Role.WAREHOUSE, Role.ACCOUNTING],
    "material.over_issue":      [Role.DIRECTOR, Role.WAREHOUSE, Role.ACCOUNTING],
    "purchase_order.created":   [Role.ACCOUNTING, Role.WAREHOUSE],
    "purchase_order.received":  [Role.PURCHASING, Role.QUALITY],  # overridden by material.received
    "work_order.released":      [Role.WAREHOUSE],
    "work_order.completed":     [Role.ACCOUNTING, Role.QUALITY],
    "non_conformance.created":  [Role.PRODUCTION, Role.DIRECTOR],
    "non_conformance.closed":   [Role.QUALITY, Role.PRODUCTION],
    "payment.due":              [Role.DIRECTOR, Role.PURCHASING],
    "receivable.overdue":       [Role.DIRECTOR],
    "stock.below_safety":       [Role.PURCHASING, Role.PRODUCTION, Role.DIRECTOR],
    "stock.over_max":           [Role.PURCHASING],
    "capacity.overloaded":      [Role.PRODUCTION, Role.DIRECTOR],
}


def get_notified_roles(event_type: str) -> list[Role]:
    """Return the list of roles that should be notified for this event."""
    return EVENT_NOTIFICATION_MAP.get(event_type, [])
