"""
Security configuration & policies — password policy, rate limiting, IP restrictions.
Centralized security settings that control system-wide security behavior.
"""
from datetime import timedelta


class PasswordPolicy:
    """Configurable password policy settings."""
    min_length: int = 8
    require_uppercase: bool = True
    require_lowercase: bool = True
    require_digit: bool = True
    require_special: bool = False
    max_age_days: int = 90          # password expiry
    history_count: int = 5           # can't reuse last N passwords
    lockout_threshold: int = 5       # failed attempts before lockout
    lockout_minutes: int = 15
    first_login_force_change: bool = True


class SessionPolicy:
    """Configurable session security settings."""
    max_concurrent_per_user: int = 3
    session_expiry_hours: int = 24
    idle_timeout_minutes: int = 60   # auto-logout after inactivity
    extend_on_activity: bool = True


class RateLimitPolicy:
    """API rate limiting settings."""
    login_per_minute: int = 10        # max login attempts per minute per IP
    api_per_minute: int = 120         # max API calls per minute per user
    burst_multiplier: float = 2.0     # allow short bursts


class SecuritySettings:
    """Aggregate all security policies into one settings object."""
    password = PasswordPolicy()
    session = SessionPolicy()
    rate_limit = RateLimitPolicy()
    ip_whitelist_enabled: bool = False
    ip_whitelist: list[str] = []            # e.g. ["192.168.1.0/24", "10.0.0.0/8"]
    maintenance_mode: bool = False
    suspicious_hours: list[int] = [0, 1, 2, 3, 4, 5]  # 00:00-05:59 = suspicious
    max_distance_km_per_hour: int = 500    # impossible travel detection


# Global security settings instance
security_settings = SecuritySettings()


def validate_password(password: str) -> tuple[bool, str]:
    """Validate password against current policy. Returns (valid, reason)."""
    policy = security_settings.password
    if len(password) < policy.min_length:
        return False, f"密碼長度至少 {policy.min_length} 碼"
    if policy.require_uppercase and not any(c.isupper() for c in password):
        return False, "需要至少一個大寫字母"
    if policy.require_lowercase and not any(c.islower() for c in password):
        return False, "需要至少一個小寫字母"
    if policy.require_digit and not any(c.isdigit() for c in password):
        return False, "需要至少一個數字"
    if policy.require_special and not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        return False, "需要至少一個特殊字元"
    return True, "OK"


def is_suspicious_hour() -> bool:
    """Check if current time is a suspicious hour for access."""
    from datetime import datetime
    return datetime.utcnow().hour in security_settings.suspicious_hours


def is_ip_allowed(ip: str) -> bool:
    """Check if IP is allowed (if whitelist enabled)."""
    if not security_settings.ip_whitelist_enabled:
        return True
    # Simple exact match (CIDR support would need ipaddress module)
    return ip in security_settings.ip_whitelist
