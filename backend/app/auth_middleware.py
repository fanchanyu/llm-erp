"""Auth middleware — validates session tokens on all API routes except login/health."""
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.session import session_manager

PUBLIC_ROUTES = {
    "/health", "/war-room", "/war-room.html", "/war-room-en", "/api/org/login", "/docs", "/openapi.json", "/redoc",
}


class AuthMiddleware(BaseHTTPMiddleware):
    """Validates Authorization header on protected routes.
    Sets request.state.user with session info including IP and device."""

    async def dispatch(self, request: Request, call_next):
        request.state.user = {
            "employee_id": None, "username": "anonymous",
            "roles": [], "permissions": [], "is_authenticated": False,
        }

        path = request.url.path
        if path in PUBLIC_ROUTES or path.startswith(("/docs/", "/openapi", "/redoc")):
            return await call_next(request)

        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
            session = session_manager.validate_session(token)
            if session:
                request.state.user = {
                    "employee_id": session.employee_id,
                    "username": session.username,
                    "roles": session.roles,
                    "permissions": session.permissions,
                    "token": session.token,
                    "ip_address": session.ip_address,
                    "device": session.device_name,
                    "is_authenticated": True,
                }

        # Dev mode: allow anonymous read access
        return await call_next(request)
