from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.v1.controllers import auth as auth_controller
from app.api.v1.deps import get_current_user, get_db
from app.api.v1.schemas.auth import (
    ForgotPasswordIn,
    OtpRequestIn,
    OtpRequestOut,
    OtpVerifyIn,
    OtpVerifyOut,
    PasswordLoginIn,
    RefreshTokenIn,
    ResetPasswordIn,
    SelectRoleIn,
    TokenOut,
    Verify2FAIn,
    VerifyResetOtpIn,
)
from app.db.models.user import User
from app.core.config import settings
from app.integrations.email.brevo import send_otp_email
from app.integrations.whatsapp.client import send_otp_template

router = APIRouter(prefix="/auth", tags=["auth"])
OTP_TTL_MINUTES = settings.otp_ttl_minutes
OTP_PEPPER = settings.otp_pepper
JWT_SECRET = settings.jwt_secret
JWT_TTL_MINUTES = settings.jwt_ttl_minutes


# ---------------------------------------------------------------------------
# Existing OTP login (unchanged)
# ---------------------------------------------------------------------------

@router.post("/otp/request", response_model=OtpRequestOut, status_code=200)
def request_otp(
    payload: OtpRequestIn,
    request: Request,
    db: Session = Depends(get_db),
) -> OtpRequestOut:
    return auth_controller.request_otp(
        payload_phone=payload.phone,
        request=request,
        db=db,
        otp_ttl_minutes=OTP_TTL_MINUTES,
        otp_pepper=OTP_PEPPER,
        debug=settings.debug,
        otp_debug_log_plaintext=settings.otp_debug_log_plaintext,
        otp_delivery_mode=settings.otp_delivery_mode,
        send_otp_template=send_otp_template,
        send_otp_email=send_otp_email,
    )


@router.post("/otp/verify", response_model=OtpVerifyOut, status_code=200)
def verify_otp(payload: OtpVerifyIn, db: Session = Depends(get_db)) -> OtpVerifyOut:
    return auth_controller.verify_otp(
        payload_phone=payload.phone,
        payload_otp=payload.otp,
        db=db,
        otp_pepper=OTP_PEPPER,
        jwt_secret=JWT_SECRET,
        jwt_ttl_minutes=JWT_TTL_MINUTES,
    )


@router.post("/select-role", response_model=TokenOut, status_code=200)
def select_role(
    payload: SelectRoleIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TokenOut:
    return auth_controller.select_role(
        db=db,
        user=current_user,
        school_id=payload.school_id,
        role=payload.role,
        jwt_secret=JWT_SECRET,
        jwt_ttl_minutes=JWT_TTL_MINUTES,
    )


@router.get("/me")
def get_me(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    return auth_controller.get_me(db=db, current_user=current_user)


# ---------------------------------------------------------------------------
# Password login
# ---------------------------------------------------------------------------

@router.post("/login", status_code=200)
def login_with_password(
    payload: PasswordLoginIn,
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    return auth_controller.login_with_password(
        identifier=payload.identifier,
        password=payload.password,
        remember_me=payload.remember_me,
        device_info=payload.device_info.model_dump(),
        request=request,
        db=db,
        send_otp_template=send_otp_template,
        send_otp_email=send_otp_email,
    )


@router.post("/verify-2fa", status_code=200)
def verify_2fa(payload: Verify2FAIn, db: Session = Depends(get_db)) -> dict:
    return auth_controller.verify_2fa(
        two_fa_token=payload.two_fa_token,
        otp=payload.otp,
        remember_me=payload.remember_me,
        db=db,
    )


@router.post("/refresh", status_code=200)
def refresh_token(payload: RefreshTokenIn, db: Session = Depends(get_db)) -> dict:
    return auth_controller.refresh_access_token(
        raw_refresh_token=payload.refresh_token,
        db=db,
    )


# ---------------------------------------------------------------------------
# Password reset
# ---------------------------------------------------------------------------

@router.post("/forgot-password", status_code=200)
def forgot_password(payload: ForgotPasswordIn, db: Session = Depends(get_db)) -> dict:
    return auth_controller.forgot_password(
        identifier=payload.identifier,
        db=db,
        send_otp_template=send_otp_template,
        send_otp_email=send_otp_email,
    )


@router.post("/verify-otp", status_code=200)
def verify_reset_otp(payload: VerifyResetOtpIn, db: Session = Depends(get_db)) -> dict:
    return auth_controller.verify_reset_otp(
        phone_or_email=payload.phone,
        otp=payload.otp,
        db=db,
    )


@router.post("/reset-password", status_code=200)
def reset_password(payload: ResetPasswordIn, db: Session = Depends(get_db)) -> dict:
    return auth_controller.reset_password(
        reset_token=payload.reset_token,
        new_password=payload.new_password,
        confirm_password=payload.confirm_password,
        db=db,
    )
