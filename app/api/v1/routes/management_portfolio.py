from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.api.v1.deps import get_db, get_valid_school_id, require_management
from app.api.v1.schemas.management_portfolio import (
    ManagementStaffSummaryOut,
    ManagementStudentsSummaryOut,
)
from app.db.models.user import User
from app.services import management_portfolio as management_portfolio_service

router = APIRouter(prefix="/management/portfolio", tags=["management-portfolio"])


@router.get("/students/summary", response_model=ManagementStudentsSummaryOut)
def get_management_students_summary(
    db: Session = Depends(get_db),
    school_id: int = Depends(get_valid_school_id),
    current_user: User = Depends(require_management),
) -> ManagementStudentsSummaryOut:
    return management_portfolio_service.get_students_summary(
        db=db,
        school_id=school_id,
        current_user=current_user,
    )


@router.get("/students/export.csv", response_class=PlainTextResponse)
def export_management_students_csv(
    db: Session = Depends(get_db),
    school_id: int = Depends(get_valid_school_id),
    current_user: User = Depends(require_management),
) -> PlainTextResponse:
    csv_text = management_portfolio_service.export_students_csv(
        db=db,
        school_id=school_id,
        current_user=current_user,
    )
    return PlainTextResponse(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="students-school-{school_id}.csv"'},
    )


@router.get("/staff/summary", response_model=ManagementStaffSummaryOut)
def get_management_staff_summary(
    db: Session = Depends(get_db),
    school_id: int = Depends(get_valid_school_id),
    current_user: User = Depends(require_management),
) -> ManagementStaffSummaryOut:
    return management_portfolio_service.get_staff_summary(
        db=db,
        school_id=school_id,
        current_user=current_user,
    )


@router.get("/staff/export.csv", response_class=PlainTextResponse)
def export_management_staff_csv(
    db: Session = Depends(get_db),
    school_id: int = Depends(get_valid_school_id),
    current_user: User = Depends(require_management),
) -> PlainTextResponse:
    csv_text = management_portfolio_service.export_staff_csv(
        db=db,
        school_id=school_id,
        current_user=current_user,
    )
    return PlainTextResponse(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="staff-school-{school_id}.csv"'},
    )
