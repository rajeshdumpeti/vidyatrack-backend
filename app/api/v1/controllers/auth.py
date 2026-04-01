from __future__ import annotations

from typing import Any, Callable

from fastapi import Request
from sqlalchemy.orm import Session

from app.db.models.user import User
from app.services import auth as auth_service
from app.services import auth_password as auth_password_service
from app.services import auth_password_reset as auth_password_reset_service


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


def select_role(
    *,
    db: Session,
    user: User,
    school_id: int,
    role: str,
    jwt_secret: str,
    jwt_ttl_minutes: int,
) -> dict[str, Any]:
    return auth_service.select_role(
        db=db,
        user=user,
        school_id=school_id,
        role=role,
        jwt_secret=jwt_secret,
        jwt_ttl_minutes=jwt_ttl_minutes,
    )


def get_me(*, db: Session, current_user: User) -> dict[str, Any]:
    return auth_service.get_me(db=db, current_user=current_user)


# ---------------------------------------------------------------------------
# Password login
# ---------------------------------------------------------------------------

def login_with_password(
    *,
    identifier: str,
    password: str,
    remember_me: bool,
    device_info: dict[str, Any],
    request: Request,
    db: Session,
    send_otp_template: Callable[..., Any],
    send_otp_email: Callable[..., Any],
) -> dict[str, Any]:
    return auth_password_service.login_with_password(
        identifier=identifier,
        password=password,
        remember_me=remember_me,
        device_info=device_info,
        request=request,
        db=db,
        send_otp_template=send_otp_template,
        send_otp_email=send_otp_email,
    )


def verify_2fa(*, two_fa_token: str, otp: str, remember_me: bool, db: Session) -> dict[str, Any]:
    return auth_password_service.verify_2fa(
        two_fa_token=two_fa_token,
        otp=otp,
        remember_me=remember_me,
        db=db,
    )


def refresh_access_token(*, raw_refresh_token: str, db: Session) -> dict[str, Any]:
    return auth_password_service.refresh_access_token(
        raw_refresh_token=raw_refresh_token,
        db=db,
    )


# ---------------------------------------------------------------------------
# Password reset
# ---------------------------------------------------------------------------

def forgot_password(
    *,
    identifier: str,
    db: Session,
    send_otp_template: Callable[..., Any],
    send_otp_email: Callable[..., Any],
) -> dict[str, Any]:
    return auth_password_reset_service.forgot_password(
        identifier=identifier,
        db=db,
        send_otp_template=send_otp_template,
        send_otp_email=send_otp_email,
    )


def verify_reset_otp(*, phone_or_email: str, otp: str, db: Session) -> dict[str, Any]:
    return auth_password_reset_service.verify_reset_otp(
        phone_or_email=phone_or_email,
        otp=otp,
        db=db,
    )


def reset_password(
    *,
    reset_token: str,
    new_password: str,
    confirm_password: str,
    db: Session,
) -> dict[str, Any]:
    return auth_password_reset_service.reset_password(
        reset_token=reset_token,
        new_password=new_password,
        confirm_password=confirm_password,
        db=db,
    )
