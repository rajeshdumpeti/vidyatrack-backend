from __future__ import annotations

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.v1.deps import get_db, require_management
from app.db.models.attendance_record import AttendanceRecord
from app.db.models.principal import Principal
from app.db.models.student import Student
from app.db.models.teacher import Teacher
from app.db.models.user import User
from app.db.models.user_school import UserSchool

router = APIRouter(prefix="/management/dashboard",
                   tags=["management-dashboard"])


class DashboardNotice(BaseModel):
    id: str
    title: str
    message: str
    created_at: datetime
    kind: str


class PrincipalSummary(BaseModel):
    assigned: bool
    principal_id: int | None = None
    name: str | None = None


class ManagementDashboardOut(BaseModel):
    total_students: int
    total_teachers: int
    attendance_today_pct: float
    attendance_today_present: int
    attendance_today_absent: int
    attendance_today_total: int
    principal: PrincipalSummary
    notices: list[DashboardNotice]


@router.get("", response_model=ManagementDashboardOut)
def get_management_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_management),
):
    links = db.query(UserSchool).filter(UserSchool.user_id == current_user.id).all()
    if not links:
        raise HTTPException(status_code=403, detail="missing_school_context")
    management_link = next(
        (link for link in links if str(link.role).upper() == "MANAGEMENT"),
        None,
    )
    school_id = management_link.school_id if management_link else links[0].school_id
    today = datetime.now(timezone.utc).date()

    total_students = (
        db.query(func.count(Student.id))
        .filter(Student.school_id == school_id)
        .scalar()
        or 0
    )
    total_teachers = (
        db.query(func.count(Teacher.id))
        .filter(Teacher.school_id == school_id)
        .scalar()
        or 0
    )

    present_today = (
        db.query(func.count(AttendanceRecord.id))
        .filter(
            AttendanceRecord.school_id == school_id,
            AttendanceRecord.date == today,
            AttendanceRecord.status == "present",
        )
        .scalar()
        or 0
    )
    absent_today = (
        db.query(func.count(AttendanceRecord.id))
        .filter(
            AttendanceRecord.school_id == school_id,
            AttendanceRecord.date == today,
            AttendanceRecord.status == "absent",
        )
        .scalar()
        or 0
    )
    total_today = present_today + absent_today
    attendance_pct = round(
        (present_today / total_today) * 100, 2) if total_today else 0.0

    principal = (
        db.query(Principal)
        .filter(Principal.school_id == school_id)
        .first()
    )

    return ManagementDashboardOut(
        total_students=total_students,
        total_teachers=total_teachers,
        attendance_today_pct=attendance_pct,
        attendance_today_present=present_today,
        attendance_today_absent=absent_today,
        attendance_today_total=total_today,
        principal=PrincipalSummary(
            assigned=principal is not None,
            principal_id=principal.id if principal else None,
            name=principal.name if principal else None,
        ),
        notices=[],
    )
