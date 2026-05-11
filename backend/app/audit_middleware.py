"""
Audit Log — automatically records all API write operations.
Tracks: who did what, when, to which resource, with what data.
"""
import uuid
from datetime import datetime
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.database import async_session
from app.models.audit_log import AuditLog
from app.models.organization import Employee


class AuditMiddleware(BaseHTTPMiddleware):
    """Records all POST/PUT/PATCH/DELETE API operations to audit_logs."""

    async def dispatch(self, request: Request, call_next):
        if request.method in ("POST", "PUT", "PATCH", "DELETE") and request.url.path.startswith("/api/"):
            # Read request body (can only be read once, so we need to consume it)
            body = None
            try:
                body_bytes = await request.body()
                body = body_bytes.decode("utf-8")[:2000] if body_bytes else None
            except Exception:
                pass

            response = await call_next(request)

            # Log the operation asynchronously (don't block response)
            try:
                user = getattr(request.state, "user", {})
                username = user.get("username", "anonymous")
                emp_name = user.get("employee_id", "")

                async with async_session() as db:
                    log = AuditLog(
                        session_id=username,
                        user_input=f"{request.method} {request.url.path}",
                        intent=request.method,
                        action=request.url.path,
                        params={"body": body, "status": response.status_code},
                        result="success" if response.status_code < 400 else "failed",
                        success=response.status_code < 400,
                    )
                    db.add(log)
                    await db.commit()
            except Exception:
                pass  # Audit log failures shouldn't break the request

            return response

        return await call_next(request)
