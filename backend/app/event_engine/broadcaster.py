"""SSE (Server-Sent Events) broadcaster — real-time push to web + mobile.

Subscribes to the EventBus and pushes events to all connected clients
via SSE. Maintains per-role queues so each client only receives events
they're authorized to see.

Both web (React) and mobile (React Native) use the same SSE endpoint
with their JWT token — the backend handles role-based filtering.
"""
from __future__ import annotations
import asyncio
import json
import logging
from typing import Optional
from .events import DomainEvent
from .event_bus import get_bus
from .role_config import get_notified_roles

logger = logging.getLogger(__name__)

# ─── SSE Connection Manager ─────────────────────────────────────

class SSEManager:
    """Manages SSE client connections, grouped by role.

    Each connected client gets an asyncio.Queue. When an event is emitted
    from the EventBus, it's pushed to the queues of all matching roles.
    """

    def __init__(self):
        self._connections: dict[str, list[asyncio.Queue]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, role: str) -> asyncio.Queue:
        """Register a new SSE connection for a given role. Returns a queue."""
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        async with self._lock:
            if role not in self._connections:
                self._connections[role] = []
            self._connections[role].append(queue)
            logger.info("SSE client connected: role=%s, total=%d",
                        role, len(self._connections[role]))
        return queue

    async def disconnect(self, role: str, queue: asyncio.Queue):
        """Remove an SSE connection."""
        async with self._lock:
            if role in self._connections:
                try:
                    self._connections[role].remove(queue)
                    logger.info("SSE client disconnected: role=%s", role)
                except ValueError:
                    pass

    async def broadcast(self, event_type: str, data: dict,
                        target_roles: list[str]):
        """Push an event to all clients whose role is in target_roles.

        If target_roles is empty, broadcasts to ALL roles.
        """
        async with self._lock:
            for role, queues in self._connections.items():
                if target_roles and role not in target_roles:
                    continue
                message = json.dumps({
                    "type": "event",
                    "event_type": event_type,
                    "data": data,
                    "timestamp": data.get("timestamp", ""),
                }, ensure_ascii=False)
                for queue in list(queues):
                    try:
                        queue.put_nowait(message)
                    except asyncio.QueueFull:
                        # Drop oldest message to keep connection alive
                        try:
                            queue.get_nowait()
                            queue.put_nowait(message)
                        except asyncio.QueueEmpty:
                            pass

    async def broadcast_all(self, event_type: str, data: dict):
        """Broadcast to ALL connected clients regardless of role."""
        await self.broadcast(event_type, data, target_roles=[])

    def get_stats(self) -> dict:
        return {
            role: len(queues)
            for role, queues in self._connections.items()
        }


# Global singleton
_manager: Optional[SSEManager] = None


def get_sse_manager() -> SSEManager:
    global _manager
    if _manager is None:
        _manager = SSEManager()
    return _manager


def reset_sse_manager():
    global _manager
    _manager = None


# ─── EventBus Wiring ────────────────────────────────────────────

def _sse_event_handler(event: DomainEvent):
    """Called by EventBus for every emitted event.

    Determines which roles should receive this event and broadcasts it.
    """
    from .role_config import get_notified_roles
    from .notification import format_notification

    target_roles = get_notified_roles(event.event_type)
    target_role_values = [r.value for r in target_roles]
    notif = format_notification(event)

    logger.info("SSE handler: event=%s target_roles=%s", event.event_type, target_role_values)

    # Schedule the async broadcast (must not block the EventBus thread)
    manager = get_sse_manager()
    try:
        asyncio.ensure_future(
            manager.broadcast(event.event_type, notif, target_role_values)
        )
        logger.info("SSE broadcast scheduled for %s", event.event_type)
    except RuntimeError as e:
        logger.error("SSE broadcast failed (no event loop): %s", e)


def init_broadcaster():
    """Wire SSE broadcaster into the EventBus.

    Call once at app startup alongside init_notification_system().
    """
    bus = get_bus()
    bus.subscribe_all(_sse_event_handler)
    logger.info("SSE broadcaster initialized — pushing events to web + mobile clients")
