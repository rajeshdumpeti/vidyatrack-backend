"""
Password-based login service.

Flow:
  1. Resolve identifier (email or phone) to a User
  2. Check account is active and not locked
  3. Verify bcrypt password hash
  4. On failure: increment failed_login_attempts, lock after 5 failures (30 min)
  5. On success:
     - super_admin: send 2FA OTP, return {requires_2fa: true, two_fa_token}
     - others: issue access + refresh tokens, write audit log
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.phone import to_e164
from app.core.roles import normalize_role
from app.db.models.otp_request import OtpRequest
from app.db.models.user import User
from app.db.repositories import auth_password as repo
from app.db.repositories import auth as auth_repo

logger = logging.getLogger(__name__)

LOGIN_MAX_ATTEMPTS = 5
LOCKOUT_MINUTES = 30
ACCESS_TOKEN_HOURS = 8
REFRESH_TOKEN_DAYS_DEFAULT = 1
REFRESH_TOKEN_DAYS_REMEMBER_ME = 30

# Portal redirect URLs by role
PORTAL_URLS: dict[str, str] = {
    "super_admin": "/platform",
    "management": "/management",
    "principal": "/principal",
    "teacher": "/teacher",
}

# Permissions by role
ROLE_PERMISSIONS: dict[str, list[str]] = {
    "super_admin": ["schools:read", "schools:write", "users:read", "users:write", "platform:admin"],
    "management": ["school:read", "school:write", "teachers:read", "teachers:write", "students:read"],
    "principal": ["school:read", "teachers:read", "students:read", "attendance:read", "marks:read"],
    "teacher": ["attendance:write", "marks:write", "students:read"],
}


def _hash_otp(phone: str, otp: str, *, otp_pepper: str) -> str:
    payload = f"{phone}:{otp}:{otp_pepper}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _b64url_encode(data: bytes) -> str:
    import base64
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def _jwt_encode(payload: dict[str, Any], *, secret: str) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    h = _b64url_encode(json.dumps(header, separators=(",", ":")).encode())
    p = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    sig_input = f"{h}.{p}".encode()
    sig = hmac.new(secret.encode(), sig_input, hashlib.sha256).digest()
    return f"{h}.{p}.{_b64url_encode(sig)}"


def _get_client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


def _resolve_user(db: Session, identifier: str) -> User | None:
    """Find active user by email or phone."""
    identifier = identifier.strip()
    if "@" in identifier:
        return repo.get_active_user_by_email(db, email=identifier)
    try:
        phone = to_e164(identifier)
        return repo.get_active_user_by_phone(db, phone=phone)
    except ValueError:
        return None


def _build_user_data(user: User, db: Session) -> dict[str, Any]:
    role = normalize_role(user.role).lower()
    school_id = None
    school_name = None
    school_status = None

    schools = auth_repo.list_active_user_school_roles(db, user_id=user.id)
    if schools:
        first = schools[0]
        school_id = first.school_id
        school_name = first.school.name if first.school else None
        school_status = "active" if getattr(first.school, "is_active", True) else "suspended"

    return {
        "id": str(user.id),
        "full_name": user.full_name,
        "email": user.email,
        "phone": user.phone,
        "role": role,
        "avatar_url": user.avatar_url,
        "school_id": str(school_id) if school_id else None,
        "school_name": school_name,
        "school_status": school_status,
        "is_first_login": user.is_first_login,
        "permissions": ROLE_PERMISSIONS.get(role, []),
        "portal_redirect_url": PORTAL_URLS.get(role, "/"),
        "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
    }


def login_with_password(
    *,
    identifier: str,
    password: str,
    remember_me: bool,
    device_info: dict[str, Any],
    request: Request,
    db: Session,
    send_otp_template: Any,
    send_otp_email: Any,
) -> dict[str, Any]:
    import bcrypt

    now = datetime.now(timezone.utc)
    ip = _get_client_ip(request)
    device_type = device_info.get("device_type")
    browser = device_info.get("browser")
    user_agent = device_info.get("user_agent")

    user = _resolve_user(db, identifier)

    # Account not found — return same error as wrong password (prevent enumeration)
    if not user:
        repo.write_audit_log(
            db, event="login_failure", identifier=identifier,
            ip_address=ip, device_type=device_type, browser=browser, user_agent=user_agent,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "INVALID_CREDENTIALS",
                "message": "Incorrect email/phone or password.",
                "lockout_until": None,
                "attempts_remaining": None,
                "support_contact": "+919876543210",
            },
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "ACCOUNT_INACTIVE",
                "message": "Your account has been deactivated. Contact your administrator.",
                "lockout_until": None,
                "attempts_remaining": None,
                "support_contact": "+919876543210",
            },
        )

    # Check lockout
    if user.locked_until and user.locked_until > now:
        minutes_left = int((user.locked_until - now).total_seconds() / 60) + 1
        repo.write_audit_log(
            db, event="login_locked", user_id=user.id, identifier=identifier,
            ip_address=ip, device_type=device_type, browser=browser, user_agent=user_agent,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "ACCOUNT_LOCKED",
                "message": f"Account locked. Try again in {minutes_left} minutes.",
                "lockout_until": user.locked_until.isoformat(),
                "attempts_remaining": 0,
                "support_contact": "+919876543210",
            },
        )

    # Verify password
    if not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "NO_PASSWORD_SET",
                "message": "This account has no password set. Use OTP login or reset your password.",
                "lockout_until": None,
                "attempts_remaining": None,
                "support_contact": "+919876543210",
            },
        )

    password_valid = bcrypt.checkpw(
        password.encode("utf-8"),
        user.password_hash.encode("utf-8"),
    )

    if not password_valid:
        user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
        attempts_remaining = max(0, LOGIN_MAX_ATTEMPTS - user.failed_login_attempts)

        if user.failed_login_attempts >= LOGIN_MAX_ATTEMPTS:
            user.locked_until = now + timedelta(minutes=LOCKOUT_MINUTES)
            db.add(user)
            db.commit()
            repo.write_audit_log(
                db, event="login_locked", user_id=user.id, identifier=identifier,
                ip_address=ip, device_type=device_type, browser=browser, user_agent=user_agent,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "code": "ACCOUNT_LOCKED",
                    "message": f"Account locked after {LOGIN_MAX_ATTEMPTS} failed attempts. Try again in {LOCKOUT_MINUTES} minutes.",
                    "lockout_until": user.locked_until.isoformat(),
                    "attempts_remaining": 0,
                    "support_contact": "+919876543210",
                },
            )

        db.add(user)
        db.commit()
        repo.write_audit_log(
            db, event="login_failure", user_id=user.id, identifier=identifier,
            ip_address=ip, device_type=device_type, browser=browser, user_agent=user_agent,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "INVALID_CREDENTIALS",
                "message": "Incorrect email/phone or password.",
                "lockout_until": None,
                "attempts_remaining": attempts_remaining,
                "support_contact": "+919876543210",
            },
        )

    # Password valid — reset failed attempts
    user.failed_login_attempts = 0
    user.locked_until = None
    db.add(user)
    db.commit()

    # Super admin requires 2FA
    role = normalize_role(user.role).lower()
    if role == "super_admin":
        return _trigger_2fa(
            user=user, now=now, db=db,
            send_otp_template=send_otp_template,
            send_otp_email=send_otp_email,
        )

    return _issue_tokens(
        user=user, now=now, remember_me=remember_me, db=db,
        identifier=identifier, ip=ip,
        device_type=device_type, browser=browser, user_agent=user_agent,
    )


def _trigger_2fa(
    *,
    user: User,
    now: datetime,
    db: Session,
    send_otp_template: Any,
    send_otp_email: Any,
) -> dict[str, Any]:
    """Send 2FA OTP and return a short-lived session token."""
    otp = f"{secrets.randbelow(1_000_000):06d}"
    otp_hash = _hash_otp(user.phone, otp, otp_pepper=settings.otp_pepper)
    expires_at = now + timedelta(minutes=settings.otp_ttl_minutes)

    row = OtpRequest(
        phone=user.phone,
        otp_hash=otp_hash,
        expires_at=expires_at,
        attempt_count=0,
        purpose="login_2fa",
        channel="WHATSAPP",
        status="PENDING",
        attempts=1,
        provider_message_id=None,
        sent_at=None,
        consumed_at=None,
    )
    db.add(row)
    db.commit()

    # Send OTP (WhatsApp → email fallback)
    delivery_mode = settings.otp_delivery_mode.strip().lower()
    if delivery_mode != "local_log_only":
        try:
            wa_result = send_otp_template(phone=user.phone, otp=otp)
            if wa_result.success:
                row.status = "SENT"
                row.sent_at = now
                db.add(row)
                db.commit()
            elif user.email:
                send_otp_email(to_email=user.email, otp=otp)
        except Exception:
            logger.exception("2FA OTP delivery failed for user_id=%s", user.id)

    logger.info("2FA OTP triggered for super_admin user_id=%s otp=%s", user.id, otp)

    # Short-lived token that proves password was already verified
    exp = now + timedelta(minutes=10)
    two_fa_payload = {
        "sub": str(user.id),
        "purpose": "2fa_session",
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    two_fa_token = _jwt_encode(two_fa_payload, secret=settings.jwt_secret)

    return {
        "success": True,
        "data": {
            "requires_2fa": True,
            "two_fa_token": two_fa_token,
            "message": "OTP sent to your registered phone. Enter it to complete login.",
        },
    }


def verify_2fa(
    *,
    two_fa_token: str,
    otp: str,
    remember_me: bool,
    db: Session,
) -> dict[str, Any]:
    """Verify super admin 2FA OTP and issue final tokens."""
    import base64

    now = datetime.now(timezone.utc)

    # Decode and verify two_fa_token
    try:
        parts = two_fa_token.split(".")
        if len(parts) != 3:
            raise ValueError("invalid")
        padding = 4 - (len(parts[1]) % 4)
        payload_json = base64.urlsafe_b64decode(parts[1] + "=" * padding).decode()
        payload = json.loads(payload_json)

        if payload.get("purpose") != "2fa_session":
            raise ValueError("wrong purpose")
        if int(payload.get("exp", 0)) < int(now.timestamp()):
            raise ValueError("expired")

        user_id = int(payload["sub"])
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_2FA_SESSION", "message": "Session expired. Please log in again."},
        )

    user = db.query(User).filter(User.id == user_id, User.is_active.is_(True)).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user_not_found")

    # Verify OTP
    from app.db.repositories.auth_password import get_latest_active_otp_by_purpose
    otp_row = get_latest_active_otp_by_purpose(
        db, phone=user.phone, purpose="login_2fa", now=now,
    )
    if not otp_row:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "OTP_NOT_FOUND", "message": "OTP not found or expired."},
        )

    if (otp_row.attempt_count or 0) >= 5:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"code": "OTP_TOO_MANY_ATTEMPTS", "message": "Too many attempts. Please log in again."},
        )

    expected_hash = otp_row.otp_hash
    provided_hash = _hash_otp(user.phone, otp, otp_pepper=settings.otp_pepper)
    if not hmac.compare_digest(expected_hash, provided_hash):
        otp_row.attempt_count = (otp_row.attempt_count or 0) + 1
        db.add(otp_row)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "OTP_INVALID", "message": "Invalid OTP."},
        )

    otp_row.consumed_at = now
    db.add(otp_row)
    db.commit()

    return _issue_tokens(
        user=user, now=now, remember_me=remember_me, db=db,
        identifier=user.phone, ip=None, device_type=None, browser=None, user_agent=None,
    )


def _issue_tokens(
    *,
    user: User,
    now: datetime,
    remember_me: bool,
    db: Session,
    identifier: str,
    ip: str | None,
    device_type: str | None,
    browser: str | None,
    user_agent: str | None,
) -> dict[str, Any]:
    role = normalize_role(user.role).lower()

    # Access token (8 hours)
    access_exp = now + timedelta(hours=ACCESS_TOKEN_HOURS)
    access_payload = {
        "sub": str(user.id),
        "role": role.upper(),
        "is_super_admin": role == "super_admin",
        "iat": int(now.timestamp()),
        "exp": int(access_exp.timestamp()),
    }
    access_token = _jwt_encode(access_payload, secret=settings.jwt_secret)

    # Refresh token
    refresh_days = REFRESH_TOKEN_DAYS_REMEMBER_ME if remember_me else REFRESH_TOKEN_DAYS_DEFAULT
    refresh_exp = now + timedelta(days=refresh_days)
    raw_refresh = secrets.token_urlsafe(48)
    repo.create_refresh_token(
        db, user_id=user.id, raw_token=raw_refresh, expires_at=refresh_exp,
    )

    # Update user
    user.last_login_at = now
    if user.is_first_login:
        user.is_first_login = False
    db.add(user)
    db.commit()

    # Audit log
    repo.write_audit_log(
        db, event="login_success", user_id=user.id, identifier=identifier,
        ip_address=ip, device_type=device_type, browser=browser, user_agent=user_agent,
    )

    return {
        "success": True,
        "data": {
            "access_token": access_token,
            "refresh_token": raw_refresh,
            "token_type": "Bearer",
            "user": _build_user_data(user, db),
        },
    }


def refresh_access_token(*, raw_refresh_token: str, db: Session) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    row = repo.get_valid_refresh_token(db, raw_token=raw_refresh_token, now=now)
    if not row:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_REFRESH_TOKEN", "message": "Refresh token is invalid or expired."},
        )

    user = db.query(User).filter(User.id == row.user_id, User.is_active.is_(True)).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user_not_found")

    # Rotate: revoke old, issue new
    repo.revoke_refresh_token(db, row=row, now=now)

    role = normalize_role(user.role).lower()
    access_exp = now + timedelta(hours=ACCESS_TOKEN_HOURS)
    access_payload = {
        "sub": str(user.id),
        "role": role.upper(),
        "is_super_admin": role == "super_admin",
        "iat": int(now.timestamp()),
        "exp": int(access_exp.timestamp()),
    }
    access_token = _jwt_encode(access_payload, secret=settings.jwt_secret)

    new_raw_refresh = secrets.token_urlsafe(48)
    new_refresh_exp = now + timedelta(days=REFRESH_TOKEN_DAYS_DEFAULT)
    repo.create_refresh_token(db, user_id=user.id, raw_token=new_raw_refresh, expires_at=new_refresh_exp)

    return {
        "success": True,
        "data": {
            "access_token": access_token,
            "refresh_token": new_raw_refresh,
            "token_type": "Bearer",
        },
    }
