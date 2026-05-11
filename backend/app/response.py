"""
Unified API response format and error handling.
All API endpoints should use these helpers for consistent responses.
"""
from typing import Any, Optional
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class APIResponse(BaseModel):
    """Standard API envelope: {success, data, meta, error}"""
    success: bool
    data: Any = None
    meta: Optional[dict] = None
    error: Optional[dict] = None


def ok(data: Any = None, meta: Optional[dict] = None, status_code: int = 200) -> JSONResponse:
    """Successful response."""
    return JSONResponse(
        status_code=status_code,
        content={"success": True, "data": data, "meta": meta, "error": None},
    )


def fail(error: str, code: str = "BAD_REQUEST", status_code: int = 400,
         details: Any = None) -> JSONResponse:
    """Error response with structured error info."""
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "data": None,
            "meta": None,
            "error": {
                "code": code,
                "message": error,
                "details": details,
            },
        },
    )


def not_found(message: str = "Resource not found") -> JSONResponse:
    return fail(message, "NOT_FOUND", 404)


def unauthorized(message: str = "Unauthorized") -> JSONResponse:
    return fail(message, "UNAUTHORIZED", 401)


def forbidden(message: str = "Forbidden") -> JSONResponse:
    return fail(message, "FORBIDDEN", 403)


def validation_error(errors: Any) -> JSONResponse:
    return fail("Validation failed", "VALIDATION_ERROR", 422, errors)


# ─── Global Exception Handlers ────────────────────────────────────

def add_exception_handlers(app):
    """Register global exception handlers on a FastAPI app."""

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request, exc):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "data": None,
                "meta": None,
                "error": {
                    "code": _status_to_code(exc.status_code),
                    "message": exc.detail,
                    "details": None,
                },
            },
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request, exc):
        # In production, log the full traceback here
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "data": None,
                "meta": None,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred",
                    "details": None,  # Never expose stack traces in production
                },
            },
        )


def _status_to_code(status: int) -> str:
    mapping = {
        400: "BAD_REQUEST", 401: "UNAUTHORIZED", 403: "FORBIDDEN",
        404: "NOT_FOUND", 422: "VALIDATION_ERROR", 429: "RATE_LIMITED",
        500: "INTERNAL_ERROR", 502: "BAD_GATEWAY", 503: "SERVICE_UNAVAILABLE",
    }
    return mapping.get(status, "UNKNOWN")
