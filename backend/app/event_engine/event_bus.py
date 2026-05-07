"""In-process event bus for cross-role coordination.

Publish-subscribe pattern: any domain action emits a DomainEvent,
and the bus routes it to all registered subscribers (notification
dispatchers, audit loggers, constraint checkers, etc.).
"""
from __future__ import annotations
import logging
import threading
from collections import defaultdict
from typing import Callable, List
from .events import DomainEvent, EventCategory, EventSeverity

logger = logging.getLogger(__name__)

# Type alias for event handlers
EventHandler = Callable[[DomainEvent], None]


class EventBus:
    """Simple in-process event bus.

    Thread-safe. Supports subscribe by event_type prefix, category, and severity.
    """

    def __init__(self):
        self._lock = threading.Lock()
        # Subscribers keyed by event_type (exact match)
        self._subscribers: dict[str, list[EventHandler]] = defaultdict(list)
        # Wildcard subscribers (receive ALL events)
        self._wildcards: list[EventHandler] = []
        # Category subscribers
        self._cat_subscribers: dict[EventCategory, list[EventHandler]] = defaultdict(list)

    def subscribe(self, event_type: str, handler: EventHandler):
        with self._lock:
            self._subscribers[event_type].append(handler)

    def subscribe_category(self, category: EventCategory, handler: EventHandler):
        with self._lock:
            self._cat_subscribers[category].append(handler)

    def subscribe_all(self, handler: EventHandler):
        with self._lock:
            self._wildcards.append(handler)

    def emit(self, event: DomainEvent):
        """Publish an event to all matching subscribers."""
        with self._lock:
            exact = list(self._subscribers.get(event.event_type, []))
            cat = list(self._cat_subscribers.get(event.category, []))
            wild = list(self._wildcards)
        for handler in exact:
            self._safe_call(handler, event)
        for handler in cat:
            self._safe_call(handler, event)
        for handler in wild:
            self._safe_call(handler, event)

    def _safe_call(self, handler: EventHandler, event: DomainEvent):
        try:
            handler(event)
        except Exception:
            logger.exception("Event handler %s failed for %s", handler.__name__, event.event_type)


# Global singleton
_bus: EventBus | None = None


def get_bus() -> EventBus:
    global _bus
    if _bus is None:
        _bus = EventBus()
    return _bus


def reset_bus():
    """For testing — clear all subscribers."""
    global _bus
    _bus = EventBus()
