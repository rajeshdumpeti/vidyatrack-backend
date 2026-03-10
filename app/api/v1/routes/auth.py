from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.v1.controllers import auth as auth_controller
from app.api.v1.deps import get_current_user, get_db
from app.api.v1.schemas.auth import OtpRequestIn, OtpRequestOut, OtpVerifyIn, TokenOut
from app.db.models.user import User
from app.core.config import settings
from app.integrations.email.brevo import send_otp_email
from app.integrations.whatsapp.client import send_otp_template

router = APIRouter(prefix="/auth", tags=["auth"])
OTP_TTL_MINUTES = settings.otp_ttl_minutes
OTP_PEPPER = settings.otp_pepper
JWT_SECRET = settings.jwt_secret
JWT_TTL_MINUTES = settings.jwt_ttl_minutes


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


@router.post("/otp/verify", response_model=TokenOut, status_code=200)
def verify_otp(payload: OtpVerifyIn, db: Session = Depends(get_db)) -> TokenOut:
    return auth_controller.verify_otp(
        payload_phone=payload.phone,
        payload_otp=payload.otp,
        db=db,
        otp_pepper=OTP_PEPPER,
        jwt_secret=JWT_SECRET,
        jwt_ttl_minutes=JWT_TTL_MINUTES,
    )


@router.get("/me")
def get_me(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    return auth_controller.get_me(db=db, current_user=current_user)
