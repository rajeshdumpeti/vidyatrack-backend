from __future__ import annotations

import hashlib
import hmac
import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.orm import Session

from app.api.v1.deps import get_db, require_management
from app.api.v1.routes.auth import OtpRequestIn, request_otp
from app.core.config import settings
from app.core.phone import normalize_phone_for_otp, phone_candidates
from app.db.models.otp_request import OtpRequest
from app.db.models.principal import Principal
from app.db.models.principal_assignment_history import PrincipalAssignmentHistory
from app.db.models.principal_onboarding_session import PrincipalOnboardingSession
from app.db.models.user import User
from app.db.models.user_school import UserSchool
from app.services.public_id import get_tenant_code_for_school, next_public_id

router = APIRouter(prefix="/management/principal", tags=["management-principal"])
logger = logging.getLogger(__name__)


class ManagementPrincipalIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    school_id: int = Field(gt=0)
    name: str = Field(min_length=1, max_length=200)
    phone: str = Field(min_length=10, max_length=20)
    email: str | None = Field(default=None, min_length=5, max_length=255)

    @model_validator(mode="after")
    def normalize(self) -> "ManagementPrincipalIn":
        self.phone = normalize_phone_for_otp(self.phone)
        if self.email is not None:
            self.email = self.email.strip()
            if self.email == "":
                self.email = None
        self.name = self.name.strip()
        return self


class ManagementPrincipalOut(BaseModel):
    principal_id: int
    principal_public_id: str
    user_id: int
    name: str
    phone: str
    email: str | None = None


class ManagementPrincipalRegisterOut(BaseModel):
    status: str
    principal: ManagementPrincipalOut
    otp_status: str
    delivery_channel: str | None = None
    otp_error_code: str | None = None
    message: str


class ManagementPrincipalOtpRetryOut(BaseModel):
    status: str
    delivery_channel: str | None = None
    otp_error_code: str | None = None
    message: str


class PrincipalHistoryOut(BaseModel):
    id: int
    name: str
    phone: str
    email: str | None = None
    status: str
    assigned_at: datetime
    deactivated_at: datetime | None = None


class PrincipalOnboardingStartOut(BaseModel):
    status: str
    session_id: int
    phone_masked: str
    expires_at: datetime
    delivery_channel: str | None = None
    message: str


class PrincipalOnboardingResendIn(BaseModel):
    school_id: int = Field(gt=0)
    session_id: int = Field(gt=0)


class PrincipalOnboardingVerifyIn(BaseModel):
    school_id: int = Field(gt=0)
    session_id: int = Field(gt=0)
    otp: str = Field(min_length=4, max_length=8)


class PrincipalOnboardingVerifyOut(BaseModel):
    status: str
    principal: ManagementPrincipalOut
    deactivated_principals: list[PrincipalHistoryOut]
    message: str


OTP_TTL_MINUTES = settings.otp_ttl_minutes
OTP_PEPPER = settings.otp_pepper


def _hash_otp(phone: str, otp: str) -> str:
    payload = f"{phone}:{otp}:{OTP_PEPPER}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _mask_phone(phone: str) -> str:
    digits = "".join(ch for ch in phone if ch.isdigit())
    if len(digits) < 4:
        return phone
    country = "+" if phone.startswith("+") else ""
    return f"{country}*** *** {digits[-4:]}"


def _resolve_management_school_id(
    db: Session,
    current_user: User,
    requested_school_id: int | None = None,
) -> int:
    school_links = db.query(UserSchool).filter(UserSchool.user_id == current_user.id).all()
    if not school_links:
        raise HTTPException(status_code=403, detail="missing_school_context")

    if requested_school_id is not None:
        has_access = any(link.school_id == requested_school_id for link in school_links)
        if not has_access:
            raise HTTPException(status_code=403, detail="invalid_school_context")
        return requested_school_id

    management_link = next(
        (link for link in school_links if str(link.role).upper() == "MANAGEMENT"),
        None,
    )
    if management_link:
        return int(management_link.school_id)
    return int(school_links[0].school_id)


def _to_principal_out(principal: Principal, user: User) -> ManagementPrincipalOut:
    return ManagementPrincipalOut(
        principal_id=principal.id,
        principal_public_id=principal.public_id,
        user_id=user.id,
        name=principal.name,
        phone=getattr(user, "phone", ""),
        email=getattr(user, "email", None),
    )


def _list_deactivated_principals(db: Session, school_id: int) -> list[PrincipalHistoryOut]:
    rows = (
        db.query(PrincipalAssignmentHistory)
        .filter(
            PrincipalAssignmentHistory.school_id == school_id,
            PrincipalAssignmentHistory.status == "DEACTIVATED",
        )
        .order_by(PrincipalAssignmentHistory.deactivated_at.desc().nullslast())
        .all()
    )
    return [
        PrincipalHistoryOut(
            id=row.id,
            name=row.name,
            phone=row.phone,
            email=row.email,
            status=row.status,
            assigned_at=row.assigned_at,
            deactivated_at=row.deactivated_at,
        )
        for row in rows
    ]


def _deactivate_active_history(db: Session, school_id: int, replaced_by_user_id: int) -> None:
    now = datetime.now(timezone.utc)
    active_rows = (
        db.query(PrincipalAssignmentHistory)
        .filter(
            PrincipalAssignmentHistory.school_id == school_id,
            PrincipalAssignmentHistory.status == "ACTIVE",
        )
        .all()
    )
    for row in active_rows:
        row.status = "DEACTIVATED"
        row.deactivated_at = now
        row.replaced_by_user_id = replaced_by_user_id


def _record_deactivated_snapshot(
    db: Session,
    school_id: int,
    old_user: User,
    old_principal_name: str,
    replaced_by_user_id: int,
) -> None:
    db.add(
        PrincipalAssignmentHistory(
            school_id=school_id,
            user_id=old_user.id,
            replaced_by_user_id=replaced_by_user_id,
            name=old_principal_name,
            phone=getattr(old_user, "phone", ""),
            email=getattr(old_user, "email", None),
            status="DEACTIVATED",
            deactivated_at=datetime.now(timezone.utc),
        )
    )


def _record_active_snapshot(db: Session, school_id: int, principal: Principal, user: User) -> None:
    db.add(
        PrincipalAssignmentHistory(
            school_id=school_id,
            user_id=user.id,
            name=principal.name,
            phone=getattr(user, "phone", ""),
            email=getattr(user, "email", None),
            status="ACTIVE",
        )
    )


def _upsert_management_principal_internal(
    payload: ManagementPrincipalIn,
    response: Response,
    db: Session,
    current_user: User,
) -> ManagementPrincipalOut:
    school_id = _resolve_management_school_id(db, current_user, payload.school_id)
    normalized_phone = normalize_phone_for_otp(payload.phone)

    existing_principal = db.query(Principal).filter(Principal.school_id == school_id).first()

    existing_user = (
        db.query(User)
        .filter(User.phone.in_(phone_candidates(normalized_phone)))
        .first()
    )

    def _deactivate_user_if_supported(user_obj: User) -> None:
        if hasattr(user_obj, "is_active"):
            setattr(user_obj, "is_active", False)

    if existing_user:
        existing_access = (
            db.query(UserSchool)
            .filter(
                UserSchool.user_id == existing_user.id,
                UserSchool.school_id == school_id,
            )
            .first()
        )
        if not existing_access:
            db.add(UserSchool(user_id=existing_user.id, school_id=school_id, role="principal"))

        existing_user.role = "PRINCIPAL"
        if hasattr(existing_user, "is_active"):
            existing_user.is_active = True
        existing_user.phone = normalized_phone
        if payload.email is not None:
            existing_user.email = payload.email

        if existing_principal and existing_principal.user_id == existing_user.id:
            response.status_code = status.HTTP_200_OK
            existing_principal.name = payload.name
            db.commit()
            db.refresh(existing_principal)
            return _to_principal_out(existing_principal, existing_user)

        if existing_principal:
            old_user = db.query(User).filter(User.id == existing_principal.user_id).first()
            if old_user and old_user.id != existing_user.id:
                _deactivate_user_if_supported(old_user)
                _deactivate_active_history(db, school_id, existing_user.id)
                _record_deactivated_snapshot(
                    db,
                    school_id,
                    old_user,
                    existing_principal.name,
                    existing_user.id,
                )

            existing_principal.user_id = existing_user.id
            existing_principal.name = payload.name
            _record_active_snapshot(db, school_id, existing_principal, existing_user)
            db.commit()
            db.refresh(existing_principal)
            return _to_principal_out(existing_principal, existing_user)

        principal = Principal(
            school_id=school_id,
            user_id=existing_user.id,
            name=payload.name,
            public_id=next_public_id(
                db,
                tenant_code=get_tenant_code_for_school(db, school_id),
                entity="principal",
            ),
        )
        db.add(principal)
        db.flush()
        _record_active_snapshot(db, school_id, principal, existing_user)
        db.commit()
        db.refresh(principal)
        return _to_principal_out(principal, existing_user)

    user = User(
        phone=normalized_phone,
        role="PRINCIPAL",
        is_active=True,
        email=payload.email,
    )
    db.add(user)
    db.flush()
    db.add(UserSchool(user_id=user.id, school_id=school_id, role="principal"))

    if existing_principal:
        old_user = db.query(User).filter(User.id == existing_principal.user_id).first()
        if old_user and old_user.id != user.id:
            _deactivate_user_if_supported(old_user)
            _deactivate_active_history(db, school_id, user.id)
            _record_deactivated_snapshot(
                db,
                school_id,
                old_user,
                existing_principal.name,
                user.id,
            )

        existing_principal.user_id = user.id
        existing_principal.name = payload.name
        _record_active_snapshot(db, school_id, existing_principal, user)
        db.commit()
        db.refresh(existing_principal)
        return _to_principal_out(existing_principal, user)

    principal = Principal(
        school_id=school_id,
        user_id=user.id,
        name=payload.name,
        public_id=next_public_id(
            db,
            tenant_code=get_tenant_code_for_school(db, school_id),
            entity="principal",
        ),
    )
    db.add(principal)
    db.flush()
    _record_active_snapshot(db, school_id, principal, user)
    db.commit()
    db.refresh(principal)
    return _to_principal_out(principal, user)


def _consume_valid_otp(db: Session, phone: str, otp: str) -> None:
    now = datetime.now(timezone.utc)
    normalized_phone = normalize_phone_for_otp(phone)

    otp_row = (
        db.query(OtpRequest)
        .filter(
            OtpRequest.phone == normalized_phone,
            OtpRequest.consumed_at.is_(None),
            OtpRequest.expires_at > now,
        )
        .order_by(OtpRequest.id.desc())
        .first()
    )

    if not otp_row:
        latest_any = (
            db.query(OtpRequest)
            .filter(
                OtpRequest.phone == normalized_phone,
                OtpRequest.consumed_at.is_(None),
            )
            .order_by(OtpRequest.id.desc())
            .first()
        )
        if latest_any and latest_any.expires_at <= now:
            raise HTTPException(status_code=400, detail="otp_expired")
        raise HTTPException(status_code=400, detail="otp_not_found")

    provided_hash = _hash_otp(normalized_phone, otp)
    if not hmac.compare_digest(otp_row.otp_hash, provided_hash):
        otp_row.attempt_count = (otp_row.attempt_count or 0) + 1
        db.add(otp_row)
        db.commit()
        raise HTTPException(status_code=400, detail="otp_invalid")

    otp_row.consumed_at = now
    db.add(otp_row)
    db.commit()


@router.get("", response_model=ManagementPrincipalOut | None, status_code=200)
def get_management_principal(
    school_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_management),
):
    school_id = _resolve_management_school_id(db, current_user, school_id)

    principal = db.query(Principal).filter(Principal.school_id == school_id).first()
    if not principal:
        return None

    user = db.query(User).filter(User.id == principal.user_id).first()
    if not user:
        return None

    return _to_principal_out(principal, user)


@router.get("/history", response_model=list[PrincipalHistoryOut])
def list_principal_history(
    school_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_management),
):
    school_id = _resolve_management_school_id(db, current_user, school_id)
    return _list_deactivated_principals(db, school_id)


@router.post("/onboarding/start", response_model=PrincipalOnboardingStartOut, status_code=200)
def start_principal_onboarding(
    payload: ManagementPrincipalIn,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_management),
):
    school_id = _resolve_management_school_id(db, current_user, payload.school_id)

    otp_result = request_otp(OtpRequestIn(phone=payload.phone), request, db)

    session = PrincipalOnboardingSession(
        school_id=school_id,
        requested_by_user_id=current_user.id,
        name=payload.name,
        phone=normalize_phone_for_otp(payload.phone),
        email=payload.email,
        status="PENDING",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=OTP_TTL_MINUTES),
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    return PrincipalOnboardingStartOut(
        status="otp_sent",
        session_id=session.id,
        phone_masked=_mask_phone(session.phone),
        expires_at=session.expires_at,
        delivery_channel=otp_result.get("delivery_channel"),
        message="OTP sent. Verify to complete principal assignment.",
    )


@router.post("/onboarding/resend", response_model=PrincipalOnboardingStartOut, status_code=200)
def resend_principal_onboarding_otp(
    payload: PrincipalOnboardingResendIn,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_management),
):
    school_id = _resolve_management_school_id(db, current_user, payload.school_id)
    session = (
        db.query(PrincipalOnboardingSession)
        .filter(
            PrincipalOnboardingSession.id == payload.session_id,
            PrincipalOnboardingSession.school_id == school_id,
        )
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="onboarding_session_not_found")
    if session.status != "PENDING":
        raise HTTPException(status_code=409, detail="onboarding_session_not_pending")

    otp_result = request_otp(OtpRequestIn(phone=session.phone), request, db)
    session.expires_at = datetime.now(timezone.utc) + timedelta(minutes=OTP_TTL_MINUTES)
    db.add(session)
    db.commit()
    db.refresh(session)

    return PrincipalOnboardingStartOut(
        status="otp_sent",
        session_id=session.id,
        phone_masked=_mask_phone(session.phone),
        expires_at=session.expires_at,
        delivery_channel=otp_result.get("delivery_channel"),
        message="OTP resent. Verify to complete principal assignment.",
    )


@router.post("/onboarding/verify", response_model=PrincipalOnboardingVerifyOut, status_code=200)
def verify_principal_onboarding(
    payload: PrincipalOnboardingVerifyIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_management),
):
    school_id = _resolve_management_school_id(db, current_user, payload.school_id)
    session = (
        db.query(PrincipalOnboardingSession)
        .filter(
            PrincipalOnboardingSession.id == payload.session_id,
            PrincipalOnboardingSession.school_id == school_id,
        )
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="onboarding_session_not_found")
    if session.status != "PENDING":
        raise HTTPException(status_code=409, detail="onboarding_session_not_pending")
    if session.expires_at <= datetime.now(timezone.utc):
        session.status = "EXPIRED"
        db.add(session)
        db.commit()
        raise HTTPException(status_code=400, detail="onboarding_session_expired")

    _consume_valid_otp(db, session.phone, payload.otp.strip())

    principal = _upsert_management_principal_internal(
        payload=ManagementPrincipalIn(
            school_id=school_id,
            name=session.name,
            phone=session.phone,
            email=session.email,
        ),
        response=Response(),
        db=db,
        current_user=current_user,
    )

    session.status = "VERIFIED"
    session.verified_at = datetime.now(timezone.utc)
    db.add(session)
    db.commit()

    return PrincipalOnboardingVerifyOut(
        status="success",
        principal=principal,
        deactivated_principals=_list_deactivated_principals(db, school_id),
        message="Principal verified and assigned successfully.",
    )


@router.post("", response_model=ManagementPrincipalOut, status_code=201)
def upsert_management_principal(
    payload: ManagementPrincipalIn,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_management),
):
    return _upsert_management_principal_internal(payload, response, db, current_user)


@router.post("/register", response_model=ManagementPrincipalRegisterOut, status_code=200)
def register_management_principal_with_otp(
    payload: ManagementPrincipalIn,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_management),
):
    upsert_response = Response()
    principal = _upsert_management_principal_internal(payload, upsert_response, db, current_user)

    try:
        otp_result = request_otp(OtpRequestIn(phone=principal.phone), request, db)
        return ManagementPrincipalRegisterOut(
            status="success",
            principal=principal,
            otp_status="sent",
            delivery_channel=otp_result.get("delivery_channel"),
            message="Principal registered successfully and OTP sent.",
        )
    except HTTPException as exc:
        logger.warning(
            "principal register otp failed school_id=%s principal_id=%s error=%s",
            payload.school_id,
            principal.principal_id,
            exc.detail,
        )
        return ManagementPrincipalRegisterOut(
            status="partial_success",
            principal=principal,
            otp_status="failed",
            otp_error_code=str(exc.detail),
            message="Principal registered, but OTP delivery failed. You can retry.",
        )


@router.post("/retry-otp", response_model=ManagementPrincipalOtpRetryOut, status_code=200)
def retry_principal_otp(
    request: Request,
    school_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_management),
):
    principal = get_management_principal(school_id=school_id, db=db, current_user=current_user)
    try:
        otp_result = request_otp(OtpRequestIn(phone=principal.phone), request, db)
        return ManagementPrincipalOtpRetryOut(
            status="success",
            delivery_channel=otp_result.get("delivery_channel"),
            message="OTP resent successfully to principal phone.",
        )
    except HTTPException as exc:
        logger.warning(
            "principal retry otp failed school_id=%s principal_id=%s error=%s",
            school_id,
            principal.principal_id,
            exc.detail,
        )
        return ManagementPrincipalOtpRetryOut(
            status="failed",
            otp_error_code=str(exc.detail),
            message="Unable to resend OTP right now. Please try again shortly.",
        )
