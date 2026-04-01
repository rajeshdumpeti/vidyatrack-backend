"""
Password reset service.

Flow:
  forgot-password  → resolve identifier → generate OTP (purpose=password_reset) → send
  verify-otp       → verify OTP hash → issue short-lived reset_token (JWT)
  reset-password   → verify reset_token → bcrypt new password → update user
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.phone import to_e164
from app.db.models.otp_request import OtpRequest
from app.db.models.user import User
from app.db.repositories import auth_password as repo

logger = logging.getLogger(__name__)

OTP_TTL_MINUTES = 10
RESET_TOKEN_TTL_MINUTES = 15


def _hash_otp(phone: str, otp: str, *, pepper: str) -> str:
    payload = f"{phone}:{otp}:{pepper}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def _jwt_encode(payload: dict[str, Any], *, secret: str) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    h = _b64url_encode(json.dumps(header, separators=(",", ":")).encode())
    p = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    sig_input = f"{h}.{p}".encode()
    sig = hmac.new(secret.encode(), sig_input, hashlib.sha256).digest()
    return f"{h}.{p}.{_b64url_encode(sig)}"


def _is_email(value: str) -> bool:
    return "@" in value


def _resolve_user(db: Session, identifier: str) -> User | None:
    identifier = identifier.strip()
    if _is_email(identifier):
        return repo.get_active_user_by_email(db, email=identifier)
    try:
        phone = to_e164(identifier)
        return repo.get_active_user_by_phone(db, phone=phone)
    except ValueError:
        return None


def forgot_password(
    *,
    identifier: str,
    db: Session,
    send_otp_template: Any,
    send_otp_email: Any,
) -> dict[str, Any]:
    """
    Always returns 200 regardless of whether the account exists (OWASP A07).
    Sends a 6-digit OTP via WhatsApp (phone) or email (email identifier).
    """
    now = datetime.now(timezone.utc)
    user = _resolve_user(db, identifier.strip())

    if not user:
        # Return generic success — do not reveal whether account exists
        logger.info("forgot_password: no user found for identifier (returning generic response)")
        return {
            "success": True,
            "message": "If an account exists with this contact, you will receive recovery instructions.",
            "method_used": "sms" if not _is_email(identifier) else "email",
            "otp_expires_in_minutes": OTP_TTL_MINUTES,
            "link_expires_in_hours": 1,
        }

    otp = f"{secrets.randbelow(1_000_000):06d}"
    phone = user.phone
    otp_hash = _hash_otp(phone, otp, pepper=settings.otp_pepper)
    expires_at = now + timedelta(minutes=OTP_TTL_MINUTES)

    row = OtpRequest(
        phone=phone,
        otp_hash=otp_hash,
        expires_at=expires_at,
        attempt_count=0,
        purpose="password_reset",
        channel="WHATSAPP",
        status="PENDING",
        attempts=1,
        provider_message_id=None,
        sent_at=None,
        consumed_at=None,
    )
    db.add(row)
    db.commit()

    # Deliver OTP — WhatsApp first, email fallback
    delivery_mode = settings.otp_delivery_mode.strip().lower()
    method_used = "sms"

    if delivery_mode == "local_log_only":
        logger.info("forgot_password local otp=%s phone_last4=%s", otp, phone[-4:])
        row.status = "SENT"
        row.channel = "LOCAL"
        row.sent_at = now
        db.add(row)
        db.commit()
    else:
        sent = False
        if not _is_email(identifier):
            try:
                wa_result = send_otp_template(phone=phone, otp=otp)
                if wa_result.success:
                    row.status = "SENT"
                    row.channel = "WHATSAPP"
                    row.sent_at = now
                    db.add(row)
                    db.commit()
                    sent = True
            except Exception:
                logger.exception("forgot_password WhatsApp delivery failed")

        if not sent and user.email:
            try:
                email_result = send_otp_email(to_email=user.email, otp=otp)
                if email_result.success:
                    row.status = "SENT"
                    row.channel = "EMAIL"
                    row.sent_at = now
                    db.add(row)
                    db.commit()
                    method_used = "email"
            except Exception:
                logger.exception("forgot_password email delivery failed")

    repo.write_audit_log(db, event="password_reset_requested", user_id=user.id, identifier=identifier)

    return {
        "success": True,
        "message": "If an account exists with this contact, you will receive recovery instructions.",
        "method_used": method_used,
        "otp_expires_in_minutes": OTP_TTL_MINUTES,
        "link_expires_in_hours": 1,
    }


def verify_reset_otp(*, phone_or_email: str, otp: str, db: Session) -> dict[str, Any]:
    """Verify password-reset OTP and return a short-lived reset_token."""
    now = datetime.now(timezone.utc)

    # Resolve to phone for OTP lookup
    user = _resolve_user(db, phone_or_email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "OTP_NOT_FOUND", "message": "OTP not found or expired."},
        )

    otp_row = repo.get_latest_active_otp_by_purpose(
        db, phone=user.phone, purpose="password_reset", now=now,
    )
    if not otp_row:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "OTP_NOT_FOUND", "message": "OTP not found or expired."},
        )

    if (otp_row.attempt_count or 0) >= 5:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"code": "OTP_TOO_MANY_ATTEMPTS", "message": "Too many attempts. Please request a new OTP."},
        )

    expected = otp_row.otp_hash
    provided = _hash_otp(user.phone, otp, pepper=settings.otp_pepper)
    if not hmac.compare_digest(expected, provided):
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

    # Issue short-lived reset_token
    exp = now + timedelta(minutes=RESET_TOKEN_TTL_MINUTES)
    reset_payload = {
        "sub": str(user.id),
        "purpose": "password_reset",
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    reset_token = _jwt_encode(reset_payload, secret=settings.jwt_secret)

    return {"success": True, "data": {"reset_token": reset_token}}


def reset_password(*, reset_token: str, new_password: str, confirm_password: str, db: Session) -> dict[str, Any]:
    """Set a new password using a verified reset_token."""
    import bcrypt

    now = datetime.now(timezone.utc)

    if new_password != confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "PASSWORD_MISMATCH", "message": "Passwords do not match."},
        )

    # Validate password complexity (min 8, at least one letter and one number)
    if len(new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "PASSWORD_TOO_SHORT", "message": "Password must be at least 8 characters."},
        )
    if not re.search(r"[A-Za-z]", new_password) or not re.search(r"[0-9]", new_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "PASSWORD_TOO_WEAK", "message": "Password must contain at least one letter and one number."},
        )

    # Decode reset_token
    try:
        parts = reset_token.split(".")
        if len(parts) != 3:
            raise ValueError("invalid")
        padding = 4 - (len(parts[1]) % 4)
        payload_json = base64.urlsafe_b64decode(parts[1] + "=" * padding).decode()
        payload = json.loads(payload_json)

        if payload.get("purpose") != "password_reset":
            raise ValueError("wrong purpose")
        if int(payload.get("exp", 0)) < int(now.timestamp()):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "RESET_TOKEN_EXPIRED", "message": "Reset link has expired. Please request a new one."},
            )
        user_id = int(payload["sub"])
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_RESET_TOKEN", "message": "Invalid or expired reset token."},
        )

    user = db.query(User).filter(User.id == user_id, User.is_active.is_(True)).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user_not_found")

    hashed = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    user.password_hash = hashed
    user.failed_login_attempts = 0
    user.locked_until = None
    db.add(user)
    db.commit()

    repo.write_audit_log(db, event="password_reset_complete", user_id=user.id)

    return {"success": True, "message": "Password updated successfully. You can now log in."}
