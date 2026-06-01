from __future__ import annotations

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.v1.deps import get_db, require_super_admin
from app.api.v1.schemas.superadmin_schools import SuperadminSchoolCreateIn
from app.db.models.user import User
from app.services.superadmin_school_admin import (
    get_school_detail,
    mark_school_test_flag,
    reactivate_school,
    reset_management_password,
    suspend_school,
    update_school_from_prd_payload,
    update_school_modules,
)
from app.services.superadmin_school_create import create_school_from_prd_payload


router = APIRouter(prefix="/superadmin/schools", tags=["superadmin"])


@router.post("/create", status_code=201)
def create_school_prd(
    payload: SuperadminSchoolCreateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    return create_school_from_prd_payload(
        db,
        payload=payload.model_dump(),
        current_user=current_user,
        idempotency_key=idempotency_key,
    )


@router.get("/{school_id}")
def superadmin_school_detail(
    school_id: str,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_super_admin),
) -> dict:
    return get_school_detail(db, school_id=school_id)


class ResetManagementPasswordIn(BaseModel):
    user_id: str
    send_via: str = Field(default="sms")
    reason: str | None = None


@router.post("/{school_id}/reset-management-password")
def reset_management_password_route(
    school_id: str,
    payload: ResetManagementPasswordIn,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_super_admin),
) -> dict:
    return reset_management_password(
        db,
        school_id=school_id,
        user_id=payload.user_id,
        send_via=payload.send_via,  # type: ignore[arg-type]
        reason=payload.reason,
    )


class SuspendSchoolIn(BaseModel):
    reason: str = Field(min_length=1, max_length=500)
    notify_management: bool = True


@router.post("/{school_id}/suspend")
def suspend_school_route(
    school_id: str,
    payload: SuspendSchoolIn,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_super_admin),
) -> dict:
    return suspend_school(
        db,
        school_id=school_id,
        reason=payload.reason,
        notify_management=payload.notify_management,
    )


class ReactivateSchoolIn(BaseModel):
    notify_management: bool = True


@router.post("/{school_id}/reactivate")
def reactivate_school_route(
    school_id: str,
    payload: ReactivateSchoolIn,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_super_admin),
) -> dict:
    return reactivate_school(
        db,
        school_id=school_id,
        notify_management=payload.notify_management,
    )


class MarkTestIn(BaseModel):
    is_test: bool


@router.patch("/{school_id}")
def update_school_prd(
    school_id: str,
    payload: MarkTestIn,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_super_admin),
) -> dict:
    return mark_school_test_flag(db, school_id=school_id, is_test=payload.is_test)


class UpdateModulesIn(BaseModel):
    modules: dict[str, bool]


@router.patch("/{school_id}/modules")
def update_school_modules_route(
    school_id: str,
    payload: UpdateModulesIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
) -> dict:
    return update_school_modules(
        db,
        school_id=school_id,
        modules=payload.modules,
        current_user=current_user,
    )


@router.put("/{school_id}/edit")
def edit_school_prd(
    school_id: str,
    payload: SuperadminSchoolCreateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
) -> dict:
    return update_school_from_prd_payload(
        db,
        school_id=school_id,
        payload=payload.model_dump(),
        current_user=current_user,
    )
