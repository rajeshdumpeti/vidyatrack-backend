from __future__ import annotations

from typing import Any, Callable

from fastapi import Request
from sqlalchemy.orm import Session

from app.db.models.user import User
from app.services import auth as auth_service


def request_otp(
    *,
    payload_phone: str,
    request: Request,
    db: Session,
    otp_ttl_minutes: int,
    otp_pepper: str,
    debug: bool,
    otp_debug_log_plaintext: bool,
    otp_delivery_mode: str,
    send_otp_template: Callable[..., Any],
    send_otp_email: Callable[..., Any],
) -> dict[str, str]:
    return auth_service.request_otp(
        payload_phone=payload_phone,
        request=request,
        db=db,
        otp_ttl_minutes=otp_ttl_minutes,
        otp_pepper=otp_pepper,
        debug=debug,
        otp_debug_log_plaintext=otp_debug_log_plaintext,
        otp_delivery_mode=otp_delivery_mode,
        send_otp_template=send_otp_template,
        send_otp_email=send_otp_email,
    )


def verify_otp(
    *,
    payload_phone: str,
    payload_otp: str,
    db: Session,
    otp_pepper: str,
    jwt_secret: str,
    jwt_ttl_minutes: int,
) -> dict[str, str]:
    return auth_service.verify_otp(
        payload_phone=payload_phone,
        payload_otp=payload_otp,
        db=db,
        otp_pepper=otp_pepper,
        jwt_secret=jwt_secret,
        jwt_ttl_minutes=jwt_ttl_minutes,
    )


def get_me(*, db: Session, current_user: User) -> dict[str, Any]:
    return auth_service.get_me(db=db, current_user=current_user)
