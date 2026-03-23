from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.db.models.otp_request import OtpRequest
from app.db.models.user import User
from app.db.models.user_school import UserSchool


def get_recent_otp_request(
    db: Session,
    *,
    phone: str,
    recent_cutoff: datetime,
) -> OtpRequest | None:
    return (
        db.query(OtpRequest)
        .filter(
            OtpRequest.phone == phone,
            OtpRequest.created_at >= recent_cutoff,
            OtpRequest.consumed_at.is_(None),  # don't block re-login after a successful auth
        )
        .first()
    )


def count_hourly_otp_requests(
    db: Session,
    *,
    phone: str,
    hourly_cutoff: datetime,
) -> int:
    return (
        db.query(OtpRequest)
        .filter(
            OtpRequest.phone == phone,
            OtpRequest.created_at >= hourly_cutoff,
        )
        .count()
    )


def get_active_user_by_phone(
    db: Session,
    *,
    phone: str,
) -> User | None:
    """Exact E.164 lookup — one canonical format, one row."""
    return (
        db.query(User)
        .filter(User.is_active.is_(True), User.phone == phone)
        .first()
    )


def get_active_user_by_phone_candidates(
    db: Session,
    *,
    phone_candidates: list[str],
) -> User | None:
    """Deprecated shim — delegates to exact lookup on the first candidate."""
    if not phone_candidates:
        return None
    return get_active_user_by_phone(db, phone=next(iter(phone_candidates)))


def get_latest_active_otp_request(
    db: Session,
    *,
    phone: str,
    now: datetime,
) -> OtpRequest | None:
    return (
        db.query(OtpRequest)
        .filter(
            OtpRequest.phone == phone,
            OtpRequest.consumed_at.is_(None),
            OtpRequest.expires_at > now,
        )
        .order_by(OtpRequest.id.desc())
        .first()
    )


def get_latest_unconsumed_otp_request(db: Session, *, phone: str) -> OtpRequest | None:
    return (
        db.query(OtpRequest)
        .filter(
            OtpRequest.phone == phone,
            OtpRequest.consumed_at.is_(None),
        )
        .order_by(OtpRequest.id.desc())
        .first()
    )


def list_user_schools(db: Session, *, user_id: int) -> list[UserSchool]:
    return db.query(UserSchool).filter(UserSchool.user_id == user_id).all()
