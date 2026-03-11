from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.api.v1.schemas.school_onboarding import (
    Phase1DraftIn,
    Phase1DraftOut,
    Phase1OnboardingIn,
    Phase1ValidateIn,
)
from app.core.roles import normalize_role
from app.db.models.user import User
from app.services.school_onboarding import (
    OnboardingConflict,
    create_draft,
    create_phase1_onboarding,
    get_draft,
    update_draft,
    validate_phase1_payload,
)


def _ensure_can_onboard(current_user: User) -> None:
    if normalize_role(current_user.role) == "SUPER_ADMIN":
        return
    if not current_user.can_create_school:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "INSUFFICIENT_PERMISSIONS", "message": "cannot_create_school"},
        )


def submit_phase1_onboarding(
    *,
    payload: Phase1OnboardingIn,
    db: Session,
    current_user: User,
    idempotency_key: str | None,
) -> dict:
    try:
        return create_phase1_onboarding(
            db,
            payload=payload.model_dump(),
            current_user=current_user,
            idempotency_key=idempotency_key,
        )
    except OnboardingConflict as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "CONFLICT", "conflicts": exc.codes},
        ) from exc


def validate_phase1(
    *,
    payload: Phase1ValidateIn,
    db: Session,
    current_user: User,
) -> dict[str, object]:
    _ensure_can_onboard(current_user)
    try:
        validate_phase1_payload(
            db,
            school_code=payload.school_code,
            udise_code=payload.udise_code,
            school_email=payload.school_email,
            admin_phone=payload.admin_phone,
            admin_email=payload.admin_email,
        )
    except OnboardingConflict as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "CONFLICT", "conflicts": exc.codes},
        ) from exc
    return {"valid": True, "conflicts": []}


def create_phase1_draft_controller(
    *,
    payload: Phase1DraftIn,
    db: Session,
    current_user: User,
) -> Phase1DraftOut:
    _ensure_can_onboard(current_user)
    return create_draft(db, payload=payload.payload, current_user=current_user)


def update_phase1_draft_controller(
    *,
    draft_id: str,
    payload: Phase1DraftIn,
    db: Session,
    current_user: User,
) -> Phase1DraftOut:
    _ensure_can_onboard(current_user)
    return update_draft(
        db, draft_id=draft_id, payload=payload.payload, current_user=current_user
    )


def get_phase1_draft_controller(
    *,
    draft_id: str,
    db: Session,
    current_user: User,
) -> Phase1DraftOut:
    _ensure_can_onboard(current_user)
    return get_draft(db, draft_id=draft_id)
