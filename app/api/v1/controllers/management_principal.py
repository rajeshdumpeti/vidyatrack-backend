from __future__ import annotations

from typing import Any, Callable

from fastapi import Response
from sqlalchemy.orm import Session

from app.api.v1.schemas.management_principal import (
    ManagementPrincipalIn,
    ManagementPrincipalOtpRetryOut,
    ManagementPrincipalOut,
    ManagementPrincipalRegisterOut,
    PrincipalHistoryOut,
    PrincipalOnboardingStartOut,
    PrincipalOnboardingVerifyOut,
)
from app.db.models.user import User
from app.services import management_principal as management_principal_service


def get_management_principal(
    *,
    school_id: int | None,
    db: Session,
    current_user: User,
) -> ManagementPrincipalOut | None:
    return management_principal_service.get_management_principal(
        school_id=school_id,
        db=db,
        current_user=current_user,
    )


def list_principal_history(
    *,
    school_id: int,
    db: Session,
    current_user: User,
) -> list[PrincipalHistoryOut]:
    return management_principal_service.list_principal_history(
        school_id=school_id,
        db=db,
        current_user=current_user,
    )


def start_principal_onboarding(
    *,
    payload: ManagementPrincipalIn,
    request: Any,
    db: Session,
    current_user: User,
    request_otp_fn: Callable[..., dict[str, Any]],
    otp_request_payload_factory: Callable[..., Any],
    otp_ttl_minutes: int,
) -> PrincipalOnboardingStartOut:
    return management_principal_service.start_principal_onboarding(
        payload=payload,
        request=request,
        db=db,
        current_user=current_user,
        request_otp_fn=request_otp_fn,
        otp_request_payload_factory=otp_request_payload_factory,
        otp_ttl_minutes=otp_ttl_minutes,
    )


def resend_principal_onboarding_otp(
    *,
    school_id: int,
    session_id: int,
    request: Any,
    db: Session,
    current_user: User,
    request_otp_fn: Callable[..., dict[str, Any]],
    otp_request_payload_factory: Callable[..., Any],
    otp_ttl_minutes: int,
) -> PrincipalOnboardingStartOut:
    return management_principal_service.resend_principal_onboarding_otp(
        school_id=school_id,
        session_id=session_id,
        request=request,
        db=db,
        current_user=current_user,
        request_otp_fn=request_otp_fn,
        otp_request_payload_factory=otp_request_payload_factory,
        otp_ttl_minutes=otp_ttl_minutes,
    )


def verify_principal_onboarding(
    *,
    school_id: int,
    session_id: int,
    otp: str,
    db: Session,
    current_user: User,
    otp_pepper: str,
) -> PrincipalOnboardingVerifyOut:
    return management_principal_service.verify_principal_onboarding(
        school_id=school_id,
        session_id=session_id,
        otp=otp,
        db=db,
        current_user=current_user,
        otp_pepper=otp_pepper,
    )


def upsert_management_principal(
    *,
    payload: ManagementPrincipalIn,
    response: Response,
    db: Session,
    current_user: User,
) -> ManagementPrincipalOut:
    return management_principal_service.upsert_management_principal(
        payload=payload,
        response=response,
        db=db,
        current_user=current_user,
    )


def register_management_principal_with_otp(
    *,
    payload: ManagementPrincipalIn,
    request: Any,
    db: Session,
    current_user: User,
    request_otp_fn: Callable[..., dict[str, Any]],
    otp_request_payload_factory: Callable[..., Any],
    logger: Any,
) -> ManagementPrincipalRegisterOut:
    return management_principal_service.register_management_principal_with_otp(
        payload=payload,
        request=request,
        db=db,
        current_user=current_user,
        request_otp_fn=request_otp_fn,
        otp_request_payload_factory=otp_request_payload_factory,
        logger=logger,
    )


def retry_principal_otp(
    *,
    request: Any,
    school_id: int,
    db: Session,
    current_user: User,
    request_otp_fn: Callable[..., dict[str, Any]],
    otp_request_payload_factory: Callable[..., Any],
    logger: Any,
) -> ManagementPrincipalOtpRetryOut:
    return management_principal_service.retry_principal_otp(
        request=request,
        school_id=school_id,
        db=db,
        current_user=current_user,
        request_otp_fn=request_otp_fn,
        otp_request_payload_factory=otp_request_payload_factory,
        logger=logger,
    )
