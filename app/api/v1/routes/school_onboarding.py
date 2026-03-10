from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Response
from sqlalchemy.orm import Session

from app.api.v1.controllers import school_onboarding as school_onboarding_controller
from app.api.v1.deps import get_current_user, get_db
from app.api.v1.schemas.school_onboarding import (
    Phase1DraftIn,
    Phase1DraftOut,
    Phase1OnboardingIn,
    Phase1OnboardingOut,
    Phase1ValidateIn,
    Phase1ValidateOut,
)
from app.db.models.user import User

router = APIRouter(prefix="/platform/schools/onboarding/phase1", tags=["school-onboarding"])


@router.post("", response_model=Phase1OnboardingOut, status_code=201)
def submit_phase1_onboarding(
    payload: Phase1OnboardingIn,
    response: Response,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = school_onboarding_controller.submit_phase1_onboarding(
        payload=payload,
        db=db,
        current_user=current_user,
        idempotency_key=idempotency_key,
    )
    response.status_code = result["status"]
    return result["payload"]


@router.post("/validate", response_model=Phase1ValidateOut)
def validate_phase1(
    payload: Phase1ValidateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return school_onboarding_controller.validate_phase1(
        payload=payload,
        db=db,
        current_user=current_user,
    )


@router.post("/draft", response_model=Phase1DraftOut, status_code=201)
def create_phase1_draft(
    payload: Phase1DraftIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return school_onboarding_controller.create_phase1_draft_controller(
        payload=payload,
        db=db,
        current_user=current_user,
    )


@router.patch("/{draft_id}", response_model=Phase1DraftOut)
def update_phase1_draft(
    draft_id: str,
    payload: Phase1DraftIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return school_onboarding_controller.update_phase1_draft_controller(
        draft_id=draft_id,
        payload=payload,
        db=db,
        current_user=current_user,
    )


@router.get("/{draft_id}", response_model=Phase1DraftOut)
def get_phase1_draft(
    draft_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return school_onboarding_controller.get_phase1_draft_controller(
        draft_id=draft_id,
        db=db,
        current_user=current_user,
    )
