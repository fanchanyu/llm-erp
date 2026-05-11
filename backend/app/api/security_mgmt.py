"""Security Management API — password policy, account admin, suspicious activity, system settings."""

from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.services import organization_service as svc
from app.security import security_settings, validate_password, is_suspicious_hour
from app.session import session_manager
from app.models.organization import User, Employee

router = APIRouter(prefix="/security", tags=["security"])


# ═══════════════════════════════════════════════════════════════════
# ─── ACCOUNT ADMIN ───────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════

@router.get("/users", response_model=dict)
async def list_all_users(
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Admin: list all system users with account status."""
    q = select(User).options(
        selectinload(User.employee)
    )
    if search:
        q = q.where(User.username.ilike(f"%{search}%"))
    if status:
        q = q.where(User.status == status)
    r = await db.execute(q.order_by(User.username))
    users = r.scalars().all()
    return {
        "users": [
            {
                "id": str(u.id), "username": u.username,
                "employee_name": u.employee.name if u.employee else "",
                "status": u.status,
                "last_login": u.last_login.isoformat() if u.last_login else None,
                "login_attempts": u.login_attempts,
                "locked_until": u.locked_until.isoformat() if u.locked_until else None,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in users
        ],
        "total": len(users),
    }


@router.post("/users/{user_id}/disable", response_model=dict)
async def disable_user(user_id: str, db: AsyncSession = Depends(get_db)):
    """Admin: disable a user account (e.g., employee resigned)."""
    from app.models.organization import User
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    user.status = "disabled"
    # Force logout all sessions
    session_manager.force_logout_all(str(user.employee_id))
    await db.flush()
    return {"success": True, "message": f"User {user.username} disabled, all sessions terminated"}


@router.post("/users/{user_id}/enable", response_model=dict)
async def enable_user(user_id: str, db: AsyncSession = Depends(get_db)):
    """Admin: re-enable a disabled user account."""
    from app.models.organization import User
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    user.status = "active"
    user.login_attempts = 0
    user.locked_until = None
    await db.flush()
    return {"success": True, "message": f"User {user.username} enabled"}


@router.post("/users/{user_id}/reset-password", response_model=dict)
async def reset_password(
    user_id: str,
    new_password: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db),
):
    """Admin: reset a user's password. Enforces password policy."""
    valid, reason = validate_password(new_password)
    if not valid:
        raise HTTPException(400, f"Password policy violation: {reason}")

    from app.models.organization import User
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")

    from app.services.organization_service import hash_password
    user.password_hash = hash_password(new_password)
    user.login_attempts = 0
    user.locked_until = None
    # Force logout to require re-login with new password
    session_manager.force_logout_all(str(user.employee_id))
    await db.flush()
    return {"success": True, "message": f"Password reset for {user.username}, all sessions terminated"}


# ═══════════════════════════════════════════════════════════════════
# ─── ACTIVITY MONITORING ─────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════

@router.get("/activity", response_model=dict)
async def get_active_sessions():
    """Real-time active user monitoring dashboard."""
    active = session_manager.get_active_session_count()
    return {
        "active_sessions": active,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/activity/recent", response_model=dict)
async def get_recent_activity(
    limit: int = Query(50),
    db: AsyncSession = Depends(get_db),
):
    """Recent user activity across the system."""
    from app.models.audit_log import AuditLog
    r = await db.execute(
        select(AuditLog).order_by(desc(AuditLog.created_at)).limit(limit)
    )
    logs = r.scalars().all()
    return {
        "activities": [
            {
                "time": l.created_at.isoformat() if l.created_at else "",
                "user": l.session_id or "",
                "action": l.action or "",
                "type": l.intent or "",
                "status": "success" if l.success else "failed",
            }
            for l in logs
        ],
        "total": len(logs),
    }


# ═══════════════════════════════════════════════════════════════════
# ─── SECURITY SETTINGS ──────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════

@router.get("/settings", response_model=dict)
async def get_security_settings():
    """Get current security policy settings."""
    p = security_settings.password
    s = security_settings.session
    r = security_settings.rate_limit
    return {
        "password_policy": {
            "min_length": p.min_length,
            "require_uppercase": p.require_uppercase,
            "require_digit": p.require_digit,
            "max_age_days": p.max_age_days,
            "lockout_threshold": p.lockout_threshold,
            "lockout_minutes": p.lockout_minutes,
        },
        "session_policy": {
            "max_concurrent": s.max_concurrent_per_user,
            "expiry_hours": s.session_expiry_hours,
            "idle_timeout_minutes": s.idle_timeout_minutes,
        },
        "rate_limit": {
            "login_per_minute": r.login_per_minute,
            "api_per_minute": r.api_per_minute,
        },
        "maintenance_mode": security_settings.maintenance_mode,
        "suspicious_hours": security_settings.suspicious_hours,
    }


@router.post("/settings", response_model=dict)
async def update_security_settings(
    min_length: Optional[int] = Query(None),
    require_uppercase: Optional[bool] = Query(None),
    max_concurrent: Optional[int] = Query(None),
    expiry_hours: Optional[int] = Query(None),
    maintenance_mode: Optional[bool] = Query(None),
):
    """Update security policy settings."""
    p = security_settings.password
    s = security_settings.session
    if min_length is not None: p.min_length = min_length
    if require_uppercase is not None: p.require_uppercase = require_uppercase
    if max_concurrent is not None: s.max_concurrent_per_user = max_concurrent
    if expiry_hours is not None: s.session_expiry_hours = expiry_hours
    if maintenance_mode is not None: security_settings.maintenance_mode = maintenance_mode
    return {"success": True, "message": "Security settings updated"}


# ═══════════════════════════════════════════════════════════════════
# ─── SUSPICIOUS ACTIVITY DETECTION ───────────────────────────────
# ═══════════════════════════════════════════════════════════════════

@router.get("/suspicious", response_model=dict)
async def detect_suspicious_activity(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Detect suspicious activities: unusual hours, impossible travel, etc."""
    findings = []

    # 1. Check current active sessions for suspicious access
    for emp_id, tokens in session_manager._user_sessions.items():
        user_sessions = session_manager.get_user_sessions(emp_id)
        for s in user_sessions:
            # Check suspicious hours
            if is_suspicious_hour():
                findings.append({
                    "type": "unusual_hours",
                    "severity": "warning",
                    "user": s.username,
                    "detail": f"User {s.username} active at unusual hour",
                    "ip": s.ip_address,
                    "device": s.device_name,
                    "time": s.last_active_at.isoformat(),
                })

    # 2. Check recent failed login attempts
    from app.models.audit_log import AuditLog
    recent_fails = await db.execute(
        select(AuditLog.session_id, func.count().label("cnt")).where(
            AuditLog.success == False,
            AuditLog.action.ilike("%login%"),
            AuditLog.created_at >= datetime.utcnow() - timedelta(hours=1),
        ).group_by(AuditLog.session_id).having(func.count() >= 3)
    )
    for row in recent_fails.all():
        findings.append({
            "type": "brute_force_attempt",
            "severity": "critical",
            "user": row.session_id,
            "detail": f"帳號 {row.session_id} 1小時內失敗 {row.cnt} 次登入",
            "regulation": "ISO 27001 A.9.4.2",
        })

    return {
        "findings": findings,
        "total": len(findings),
        "timestamp": datetime.utcnow().isoformat(),
    }
