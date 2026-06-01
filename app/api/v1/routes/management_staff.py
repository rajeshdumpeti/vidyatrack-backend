from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.v1.deps import get_db, require_management
from app.api.v1.schemas.management_staff import (
    ManagementStaffCompensationUpdateIn,
    ManagementStaffListItem,
    ManagementStaffListOut,
    ManagementStaffPayrollProcessIn,
    ManagementStaffPayrollProcessOut,
    ManagementStaffStatsOut,
)
from app.db.models.user import User
from app.services import management_staff as management_staff_service

router = APIRouter(prefix="/management/staff", tags=["management-staff"])


@router.get("", response_model=ManagementStaffListOut)
def get_management_staff(
    school_id: int | None = Query(default=None),
    search: str | None = Query(default=None),
    role: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_management),
) -> ManagementStaffListOut:
    return management_staff_service.list_staff(
        db=db,
        current_user=current_user,
        school_id=school_id,
        search=search,
        role=role,
    )


@router.get("/stats", response_model=ManagementStaffStatsOut)
def get_management_staff_stats(
    school_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_management),
) -> ManagementStaffStatsOut:
    return management_staff_service.get_staff_stats(
        db=db,
        current_user=current_user,
        school_id=school_id,
    )


@router.patch("/{user_id}/compensation", response_model=ManagementStaffListItem)
def patch_management_staff_compensation(
    user_id: int,
    payload: ManagementStaffCompensationUpdateIn,
    school_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_management),
):
    item = management_staff_service.update_staff_compensation(
        db=db,
        current_user=current_user,
        user_id=user_id,
        payload=payload,
        school_id=school_id,
    )
    return item


@router.post("/payroll/process", response_model=ManagementStaffPayrollProcessOut)
def post_management_staff_payroll(
    payload: ManagementStaffPayrollProcessIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_management),
) -> ManagementStaffPayrollProcessOut:
    return management_staff_service.process_staff_payroll(
        db=db,
        current_user=current_user,
        school_id=payload.school_id,
        user_id=payload.user_id,
        payroll_month=payload.payroll_month,
        reference_note=payload.reference_note,
    )
