"""Service-level constraint enforcement.

Provides a decorator/utility that automatically runs constraint checks
before any service write operation. If BLOCKed, raises an exception.
If WARNed, attaches warnings to the response context.
"""
from __future__ import annotations
import functools
import logging
from typing import Any, Callable
from .constraint_checker import get_checker, CheckResult, ConstraintVerdict

logger = logging.getLogger(__name__)


class ConstraintBlocked(Exception):
    """Raised when a constraint BLOCKs an operation.

    The caller should catch this and return the verdicts to the user.
    """

    def __init__(self, operation: str, verdicts: list[ConstraintVerdict]):
        self.operation = operation
        self.verdicts = verdicts
        blocks = [v for v in verdicts if v.result == CheckResult.BLOCK]
        msgs = "; ".join(v.message for v in blocks)
        super().__init__(f"[{operation}] Constraint blocked: {msgs}")


class ConstraintWarning(Exception):
    """Raised when constraints produce warnings (non-blocking).

    The caller can choose to proceed or surface warnings.
    """

    def __init__(self, operation: str, verdicts: list[ConstraintVerdict]):
        self.operation = operation
        self.verdicts = verdicts
        warnings = [v for v in verdicts if v.result == CheckResult.WARN]
        msgs = "; ".join(v.message for v in warnings)
        super().__init__(f"[{operation}] Constraint warnings: {msgs}")


def enforce(operation: str, params: dict, actor_role: str = ""):
    """Run constraint checks and raise if BLOCKed.

    Usage in any service method:
        enforce("issue_material", {"item": x, "quantity": y, ...}, role)
        # if we get here, all checks passed

    Returns list of warning verdicts (non-blocking).
    """
    checker = get_checker()
    verdicts = checker.check(operation, params, actor_role)

    blocks = [v for v in verdicts if v.result == CheckResult.BLOCK]
    warnings = [v for v in verdicts if v.result == CheckResult.WARN]

    if blocks:
        raise ConstraintBlocked(operation, blocks)

    return warnings


def check(operation: str):
    """Decorator that wraps a service method with constraint enforcement.

    The decorated method must accept 'actor_role' as a keyword argument.

    Usage:
        @check("issue_material")
        async def issue_material(self, item, quantity, ..., actor_role=""):
            ...

    On BLOCK: raises ConstraintBlocked
    On WARN: attaches warnings to function result via .__warnings__ attribute
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any):
            # Extract actor_role from kwargs or default
            actor_role = kwargs.pop("actor_role", "")
            # Extract params from kwargs (excluding known non-param keys)
            param_keys = {k for k in kwargs.keys() if k not in ("db", "session", "self")}
            params = {k: kwargs[k] for k in param_keys}

            # Run constraint checks before the actual function
            warnings = enforce(operation, params, actor_role)

            # Execute the actual function
            result = await func(*args, **kwargs, actor_role=actor_role)

            # Attach warnings to result if it's a dict
            if isinstance(result, dict):
                if warnings:
                    result["__warnings__"] = [
                        {
                            "code": w.code,
                            "message": w.message,
                            "alternatives": w.alternatives,
                        }
                        for w in warnings
                    ]
            return result

        return wrapper

    return decorator
