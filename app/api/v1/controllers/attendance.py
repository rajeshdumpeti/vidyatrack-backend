from __future__ import annotations

from datetime import date as date_type

from fastapi import Response
from sqlalchemy.orm import Session

from app.api.v1.schemas.attendance import (
    AttendanceCreate,
    AttendanceOut,
    AttendanceSubmitIn,
    AttendanceUpdate,
)
from app.db.models.attendance_record import AttendanceRecord
from app.db.models.attendance_submission import AttendanceSubmission
from app.db.models.user import User
from app.services import attendance as attendance_service


def list_attendance(
    *,
    db: Session,
    school_id: int,
    date: date_type,
    section_id: int | None,
    include_defaults: bool,
) -> list[AttendanceOut]:
    return attendance_service.list_attendance(
        db=db,
        school_id=school_id,
        date=date,
        section_id=section_id,
        include_defaults=include_defaults,
    )


def create_attendance(
    *,
    payload: AttendanceCreate,
    db: Session,
    current_user: User,
    school_id: int,
) -> AttendanceRecord:
    return attendance_service.create_attendance(
        payload=payload,
        db=db,
        current_user=current_user,
        school_id=school_id,
    )


def update_attendance(
    *,
    attendance_id: int,
    payload: AttendanceUpdate,
    db: Session,
    school_id: int,
    current_user: User,
    student_id: int | None,
    date: date_type | None,
) -> AttendanceRecord:
    return attendance_service.update_attendance(
        attendance_id=attendance_id,
        payload=payload,
        db=db,
        school_id=school_id,
        current_user=current_user,
        student_id=student_id,
        date=date,
    )


def submit_attendance(
    *,
    payload: AttendanceSubmitIn,
    response: Response,
    db: Session,
    current_user: User,
    school_id: int,
) -> AttendanceSubmission:
    return attendance_service.submit_attendance(
        payload=payload,
        response=response,
        db=db,
        current_user=current_user,
        school_id=school_id,
    )
