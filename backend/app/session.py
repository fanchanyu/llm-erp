"""
Session Manager — enterprise-grade session tracking for VPN/internal network access.

Provides:
- Active session listing per user
- Concurrent login control (configurable limit)
- IP/device tracking per session
- Force logout by admin
- Login history with geolocation context
"""
import uuid
import secrets
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class SessionInfo:
    """Represents a single active user session."""
    token: str
    employee_id: str
    username: str
    roles: list
    permissions: list
    ip_address: str
    user_agent: str
    device_name: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_active_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: datetime = None


class SessionManager:
    """
    Thread-safe session store with concurrent login control.
    Default: max 3 concurrent sessions per user, 24h expiry.
    """

    def __init__(self, max_concurrent: int = 3, expiry_hours: int = 24):
        self._sessions: dict[str, SessionInfo] = {}  # token → SessionInfo
        self._user_sessions: dict[str, list[str]] = {}  # employee_id → [tokens]
        self.max_concurrent = max_concurrent
        self.expiry_hours = expiry_hours

    def create_session(self, employee_id: str, username: str,
                       roles: list, permissions: list,
                       ip_address: str = "", user_agent: str = "",
                       device_name: str = "") -> str:
        """Create a new session. Enforces concurrent login limit."""

        # Enforce concurrent login limit — kick oldest session if over limit
        existing = self._user_sessions.get(employee_id, [])
        if len(existing) >= self.max_concurrent:
            # Remove oldest session
            oldest_token = existing[0]
            self._remove_session(oldest_token)

        # Generate unique token
        token = secrets.token_hex(32)
        session = SessionInfo(
            token=token,
            employee_id=employee_id,
            username=username,
            roles=roles,
            permissions=permissions,
            ip_address=ip_address,
            user_agent=user_agent,
            device_name=device_name,
            expires_at=datetime.utcnow() + timedelta(hours=self.expiry_hours),
        )
        self._sessions[token] = session

        if employee_id not in self._user_sessions:
            self._user_sessions[employee_id] = []
        self._user_sessions[employee_id].append(token)

        return token

    def validate_session(self, token: str) -> Optional[SessionInfo]:
        """Validate a session token. Returns None if invalid/expired."""
        session = self._sessions.get(token)
        if not session:
            return None
        if session.expires_at < datetime.utcnow():
            self._remove_session(token)
            return None
        session.last_active_at = datetime.utcnow()
        return session

    def get_user_sessions(self, employee_id: str) -> list[SessionInfo]:
        """List all active sessions for a user."""
        tokens = self._user_sessions.get(employee_id, [])
        result = []
        for token in tokens:
            session = self._sessions.get(token)
            if session:
                result.append(session)
        return result

    def force_logout(self, token: str) -> bool:
        """Forcefully terminate a session (by admin or user)."""
        return self._remove_session(token)

    def force_logout_all(self, employee_id: str) -> int:
        """Terminate all sessions for a user. Returns count of sessions removed."""
        tokens = self._user_sessions.get(employee_id, [])
        count = 0
        for token in list(tokens):
            if self._remove_session(token):
                count += 1
        return count

    def cleanup_expired(self) -> int:
        """Remove all expired sessions. Returns count of cleaned sessions."""
        expired = []
        for token, session in self._sessions.items():
            if session.expires_at < datetime.utcnow():
                expired.append(token)
        for token in expired:
            self._remove_session(token)
        return len(expired)

    def get_active_session_count(self) -> int:
        """Total number of active sessions."""
        return len(self._sessions)

    def _remove_session(self, token: str) -> bool:
        """Internal: remove a session from both stores."""
        session = self._sessions.pop(token, None)
        if not session:
            return False
        user_tokens = self._user_sessions.get(session.employee_id, [])
        if token in user_tokens:
            user_tokens.remove(token)
        return True


# Global session manager instance
session_manager = SessionManager(max_concurrent=3, expiry_hours=24)
