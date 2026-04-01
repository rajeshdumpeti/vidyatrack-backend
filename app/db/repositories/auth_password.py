from __future__ import annotations

import hashlib
from datetime import datetime

from sqlalchemy.orm import Session

from app.db.models.audit_log import AuditLog
from app.db.models.otp_request import OtpRequest
from app.db.models.refresh_token import RefreshToken
from app.db.models.user import User


# ---------------------------------------------------------------------------
# User lookup
# ---------------------------------------------------------------------------

def get_active_user_by_email(db: Session, *, email: str) -> User | None:
    return (
        db.query(User)
        .filter(User.is_active.is_(True), User.email == email.lower().strip())
        .first()
    )


def get_active_user_by_phone(db: Session, *, phone: str) -> User | None:
    return (
        db.query(User)
        .filter(User.is_active.is_(True), User.phone == phone)
        .first()
    )


# ---------------------------------------------------------------------------
# Refresh tokens
# ---------------------------------------------------------------------------

def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode()).hexdigest()


def create_refresh_token(
    db: Session,
    *,
    user_id: int,
    raw_token: str,
    expires_at: datetime,
) -> RefreshToken:
    row = RefreshToken(
        user_id=user_id,
        token_hash=_hash_token(raw_token),
        expires_at=expires_at,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_valid_refresh_token(
    db: Session,
    *,
    raw_token: str,
    now: datetime,
) -> RefreshToken | None:
    token_hash = _hash_token(raw_token)
    return (
        db.query(RefreshToken)
        .filter(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > now,
        )
        .first()
    )


def revoke_refresh_token(db: Session, *, row: RefreshToken, now: datetime) -> None:
    row.revoked_at = now
    db.add(row)
    db.commit()


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------

def write_audit_log(
    db: Session,
    *,
    event: str,
    user_id: int | None = None,
    identifier: str | None = None,
    ip_address: str | None = None,
    device_type: str | None = None,
    browser: str | None = None,
    user_agent: str | None = None,
) -> None:
    row = AuditLog(
        event=event,
        user_id=user_id,
        identifier=identifier,
        ip_address=ip_address,
        device_type=device_type,
        browser=browser,
        user_agent=user_agent,
    )
    db.add(row)
    db.commit()


# ---------------------------------------------------------------------------
# OTP for 2FA and password reset
# ---------------------------------------------------------------------------

def get_latest_active_otp_by_purpose(
    db: Session,
    *,
    phone: str,
    purpose: str,
    now: datetime,
) -> OtpRequest | None:
    return (
        db.query(OtpRequest)
        .filter(
            OtpRequest.phone == phone,
            OtpRequest.purpose == purpose,
            OtpRequest.consumed_at.is_(None),
            OtpRequest.expires_at > now,
        )
        .order_by(OtpRequest.id.desc())
        .first()
    )
