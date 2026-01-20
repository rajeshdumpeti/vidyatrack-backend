from __future__ import annotations

from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.v1.deps import get_db, require_principal
from app.db.models.attendance_record import AttendanceRecord
from app.db.models.student import Student
from app.db.models.teacher import Teacher

router = APIRouter(prefix="/principal/dashboard",
                   tags=["principal-dashboard"])


class DashboardNotice(BaseModel):
    id: str
    title: str
    message: str
    created_at: datetime
    kind: str


class PrincipalDashboardOut(BaseModel):
    total_students: int
    total_teachers: int
    attendance_today_pct: float
    attendance_today_present: int
    attendance_today_absent: int
    attendance_today_total: int
    notices: list[DashboardNotice]


@router.get("", response_model=PrincipalDashboardOut)
def get_principal_dashboard(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_principal),
):
    school_id = current_user["school_id"]
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

    return PrincipalDashboardOut(
        total_students=total_students,
        total_teachers=total_teachers,
        attendance_today_pct=attendance_pct,
        attendance_today_present=present_today,
        attendance_today_absent=absent_today,
        attendance_today_total=total_today,
        notices=[],
    )
