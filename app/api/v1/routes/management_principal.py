from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.orm import Session

from app.api.v1.controllers import auth as auth_controller
from app.api.v1.controllers import management_principal as management_principal_controller
from app.api.v1.deps import get_db, require_management
from app.api.v1.schemas.auth import OtpRequestIn
from app.api.v1.schemas.management_principal import (
    ManagementPrincipalIn,
    ManagementPrincipalOtpRetryOut,
    ManagementPrincipalOut,
    ManagementPrincipalRegisterOut,
    PrincipalHistoryOut,
    PrincipalOnboardingResendIn,
    PrincipalOnboardingStartOut,
    PrincipalOnboardingVerifyIn,
    PrincipalOnboardingVerifyOut,
)
from app.core.config import settings
from app.db.models.user import User
from app.integrations.email.brevo import send_otp_email
from app.integrations.whatsapp.client import send_otp_template

router = APIRouter(prefix="/management/principal", tags=["management-principal"])
logger = logging.getLogger(__name__)


OTP_TTL_MINUTES = settings.otp_ttl_minutes
OTP_PEPPER = settings.otp_pepper


def _request_otp(payload: OtpRequestIn, request: Request, db: Session) -> dict[str, str]:
    return auth_controller.request_otp(
        payload_phone=payload.phone,
        request=request,
        db=db,
        otp_ttl_minutes=settings.otp_ttl_minutes,
        otp_pepper=settings.otp_pepper,
        debug=settings.debug,
        otp_debug_log_plaintext=settings.otp_debug_log_plaintext,
        otp_delivery_mode=settings.otp_delivery_mode,
        send_otp_template=send_otp_template,
        send_otp_email=send_otp_email,
    )


@router.get("", response_model=ManagementPrincipalOut | None, status_code=200)
def get_management_principal(
    school_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_management),
) -> ManagementPrincipalOut | None:
    return management_principal_controller.get_management_principal(
        school_id=school_id,
        db=db,
        current_user=current_user,
    )


@router.get("/history", response_model=list[PrincipalHistoryOut])
def list_principal_history(
    school_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_management),
) -> list[PrincipalHistoryOut]:
    return management_principal_controller.list_principal_history(
        school_id=school_id,
        db=db,
        current_user=current_user,
    )


@router.post("/onboarding/start", response_model=PrincipalOnboardingStartOut, status_code=200)
def start_principal_onboarding(
    payload: ManagementPrincipalIn,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_management),
) -> PrincipalOnboardingStartOut:
    return management_principal_controller.start_principal_onboarding(
        payload=payload,
        request=request,
        db=db,
        current_user=current_user,
        request_otp_fn=_request_otp,
        otp_request_payload_factory=OtpRequestIn,
        otp_ttl_minutes=OTP_TTL_MINUTES,
    )


@router.post("/onboarding/resend", response_model=PrincipalOnboardingStartOut, status_code=200)
def resend_principal_onboarding_otp(
    payload: PrincipalOnboardingResendIn,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_management),
) -> PrincipalOnboardingStartOut:
    return management_principal_controller.resend_principal_onboarding_otp(
        school_id=payload.school_id,
        session_id=payload.session_id,
        request=request,
        db=db,
        current_user=current_user,
        request_otp_fn=_request_otp,
        otp_request_payload_factory=OtpRequestIn,
        otp_ttl_minutes=OTP_TTL_MINUTES,
    )


@router.post("/onboarding/verify", response_model=PrincipalOnboardingVerifyOut, status_code=200)
def verify_principal_onboarding(
    payload: PrincipalOnboardingVerifyIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_management),
) -> PrincipalOnboardingVerifyOut:
    return management_principal_controller.verify_principal_onboarding(
        school_id=payload.school_id,
        session_id=payload.session_id,
        otp=payload.otp,
        db=db,
        current_user=current_user,
        otp_pepper=OTP_PEPPER,
    )


@router.post("", response_model=ManagementPrincipalOut, status_code=201)
def upsert_management_principal(
    payload: ManagementPrincipalIn,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_management),
) -> ManagementPrincipalOut:
    return management_principal_controller.upsert_management_principal(
        payload=payload,
        response=response,
        db=db,
        current_user=current_user,
    )


@router.post("/register", response_model=ManagementPrincipalRegisterOut, status_code=200)
def register_management_principal_with_otp(
    payload: ManagementPrincipalIn,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_management),
) -> ManagementPrincipalRegisterOut:
    return management_principal_controller.register_management_principal_with_otp(
        payload=payload,
        request=request,
        db=db,
        current_user=current_user,
        request_otp_fn=_request_otp,
        otp_request_payload_factory=OtpRequestIn,
        logger=logger,
    )


@router.post("/retry-otp", response_model=ManagementPrincipalOtpRetryOut, status_code=200)
def retry_principal_otp(
    request: Request,
    school_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_management),
) -> ManagementPrincipalOtpRetryOut:
    return management_principal_controller.retry_principal_otp(
        request=request,
        school_id=school_id,
        db=db,
        current_user=current_user,
        request_otp_fn=_request_otp,
        otp_request_payload_factory=OtpRequestIn,
        logger=logger,
    )
