"""
Auth module — JWT token creation, validation, and FastAPI dependency.
Provides authentication & authorization for all API endpoints.
"""
import uuid
import secrets
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db

# Simple token-based auth (upgrade to JWT with python-jose for production)
# We use the model's token stored in a memory/session cache

TOKEN_STORE: dict[str, dict] = {}  # token -> {employee_id, username, roles, permissions, expires_at}
TOKEN_EXPIRY_HOURS = 24
security = HTTPBearer(auto_error=False)


def create_session_token(employee_id: uuid.UUID, username: str,
                          roles: list[dict], permissions: list[dict]) -> str:
    """Create a session token and store it."""
    token = secrets.token_hex(32)
    TOKEN_STORE[token] = {
        "employee_id": str(employee_id),
        "username": username,
        "roles": roles,
        "permissions": permissions,
        "created_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(hours=TOKEN_EXPIRY_HOURS),
    }
    return token


def validate_token(token: str) -> Optional[dict]:
    """Validate a token and return user session data."""
    session = TOKEN_STORE.get(token)
    if not session:
        return None
    if session["expires_at"] < datetime.utcnow():
        del TOKEN_STORE[token]
        return None
    return session


def invalidate_token(token: str):
    """Logout: remove token from store."""
    TOKEN_STORE.pop(token, None)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    """
    FastAPI dependency: extract and validate current user from Authorization header.
    Usage: add `current_user: dict = Depends(get_current_user)` to any route.
    """
    if credentials is None:
        # For development: allow anonymous with basic read permissions
        return {
            "employee_id": None,
            "username": "anonymous",
            "roles": [],
            "permissions": [],
            "is_authenticated": False,
        }

    session = validate_token(credentials.credentials)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    return {
        "employee_id": session["employee_id"],
        "username": session["username"],
        "roles": session["roles"],
        "permissions": session["permissions"],
        "is_authenticated": True,
    }


def require_auth(current_user: dict = Depends(get_current_user)) -> dict:
    """FastAPI dependency: require authenticated user."""
    if not current_user["is_authenticated"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    return current_user


def require_permission(module: str, action: str):
    """
    FastAPI dependency factory: require a specific permission.
    Usage: `require_permission("inventory", "read")` as a dependency.
    """
    async def _check(current_user: dict = Depends(require_auth)):
        perms = current_user.get("permissions", [])
        has_perm = False
        for p in perms:
            if p.get("module") == module and p.get("action") == action:
                scope = p.get("scope", "self")
                # TODO: check scope against data context in actual route handlers
                has_perm = True
                break
        if not has_perm:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {module}/{action}",
            )
        return current_user
    return _check


def require_role(role_code: str):
    """
    FastAPI dependency factory: require a specific role.
    Usage: `require_role("admin")` as a dependency.
    """
    async def _check(current_user: dict = Depends(require_auth)):
        roles = current_user.get("roles", [])
        if not any(r.get("role_code") == role_code for r in roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role required: {role_code}",
            )
        return current_user
    return _check
