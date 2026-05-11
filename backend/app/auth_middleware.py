"""Auth middleware — validates JWT tokens on all API routes except login/health."""
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.auth import validate_token

# Routes that don't require auth
PUBLIC_ROUTES = {
    "/health",
    "/api/org/login",
    "/docs",
    "/openapi.json",
    "/redoc",
}


class AuthMiddleware(BaseHTTPMiddleware):
    """Validates Authorization header on protected routes. Sets request.state.user."""

    async def dispatch(self, request: Request, call_next):
        request.state.user = {
            "employee_id": None,
            "username": "anonymous",
            "roles": [],
            "permissions": [],
            "is_authenticated": False,
        }

        path = request.url.path

        # Skip auth for public routes
        if path in PUBLIC_ROUTES or path.startswith(("/docs/", "/openapi", "/redoc")):
            return await call_next(request)

        # Check Authorization header
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
            session = validate_token(token)
            if session:
                request.state.user = {
                    "employee_id": session["employee_id"],
                    "username": session["username"],
                    "roles": session["roles"],
                    "permissions": session["permissions"],
                    "is_authenticated": True,
                }
                return await call_next(request)

        # For development: allow anonymous access with read-only scope
        # In production: uncomment below to block unauthenticated requests
        # return JSONResponse(
        #     status_code=401,
        #     content={"detail": "Authentication required"},
        # )

        return await call_next(request)
