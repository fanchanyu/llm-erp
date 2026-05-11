"""
Auth module — session-based authentication with VPN-aware session management.
Uses SessionManager for concurrent login control, IP tracking, force logout.
"""
from typing import Optional
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.session import session_manager, SessionInfo

security = HTTPBearer(auto_error=False)


def create_session(employee_id: str, username: str,
                   roles: list, permissions: list,
                   request: Request = None) -> str:
    """Create a session from request context. Captures IP and User-Agent."""
    ip = request.client.host if request and request.client else ""
    ua = request.headers.get("User-Agent", "") if request else ""
    device = _guess_device(ua)
    return session_manager.create_session(
        employee_id=employee_id, username=username,
        roles=roles, permissions=permissions,
        ip_address=ip, user_agent=ua, device_name=device,
    )


def _guess_device(ua: str) -> str:
    ua_lower = ua.lower()
    if "mobile" in ua_lower or "android" in ua_lower or "iphone" in ua_lower:
        return "mobile"
    if "tablet" in ua_lower or "ipad" in ua_lower:
        return "tablet"
    if "windows" in ua_lower or "mac" in ua_lower or "linux" in ua_lower:
        return "desktop"
    return "unknown"


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    """FastAPI dependency: extract current user from Authorization header."""
    if credentials is None:
        return {
            "employee_id": None, "username": "anonymous",
            "roles": [], "permissions": [], "is_authenticated": False,
        }
    session = session_manager.validate_session(credentials.credentials)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return {
        "employee_id": session.employee_id,
        "username": session.username,
        "roles": session.roles,
        "permissions": session.permissions,
        "token": session.token,
        "is_authenticated": True,
    }


def require_auth(current_user: dict = Depends(get_current_user)) -> dict:
    if not current_user["is_authenticated"]:
        raise HTTPException(status_code=401, detail="Authentication required")
    return current_user


def require_permission(module: str, action: str):
    async def _check(current_user: dict = Depends(require_auth)):
        for p in current_user.get("permissions", []):
            if p.get("module") == module and p.get("action") == action:
                return current_user
        raise HTTPException(status_code=403, detail=f"Permission denied: {module}/{action}")
    return _check
