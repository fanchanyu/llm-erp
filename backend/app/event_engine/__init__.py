"""LLM-ERP Event Engine

Cross-role event-driven architecture for proactive decision support.

Components:
- events: Domain event definitions for all business operations
- event_bus: In-process pub/sub event bus
- role_config: Six ERP user archetypes with permissions
- notification: Cross-role notification dispatcher
- constraint_checker: Pre-validation of business rules
"""
from .events import (
    DomainEvent, EventCategory, EventSeverity,
    material_received, material_issued, po_created,
    wo_released, nc_created, payment_due, ar_overdue,
)
from .event_bus import EventBus, get_bus, reset_bus
from .role_config import (
    Role, RoleConfig, ROLE_CONFIGS, get_config, get_role_from_string,
    get_notified_roles, EVENT_NOTIFICATION_MAP,
)
from .notification import (
    init_notification_system, get_notifications,
    count_unread, mark_read, format_notification,
)
from .constraint_checker import (
    ConstraintChecker, ConstraintVerdict, CheckResult,
    get_checker,
)


def init_event_engine():
    """Initialize the entire event engine at app startup."""
    from .notification import init_notification_system
    init_notification_system()
