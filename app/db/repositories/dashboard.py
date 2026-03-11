from __future__ import annotations

from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models.attendance_record import AttendanceRecord
from app.db.models.principal import Principal
from app.db.models.student import Student
from app.db.models.teacher import Teacher
from app.db.models.user_school import UserSchool


def list_user_school_links(db: Session, *, user_id: int) -> list[UserSchool]:
    return db.query(UserSchool).filter(UserSchool.user_id == user_id).all()


def count_students(db: Session, *, school_id: int) -> int:
    return (
        db.query(func.count(Student.id)).filter(Student.school_id == school_id).scalar()
        or 0
    )


def count_teachers(db: Session, *, school_id: int) -> int:
    return (
        db.query(func.count(Teacher.id)).filter(Teacher.school_id == school_id).scalar()
        or 0
    )


def count_attendance_by_status(
    db: Session,
    *,
    school_id: int,
    for_date: date,
    attendance_status: str,
) -> int:
    return (
        db.query(func.count(AttendanceRecord.id))
        .filter(
            AttendanceRecord.school_id == school_id,
            AttendanceRecord.date == for_date,
            AttendanceRecord.status == attendance_status,
        )
        .scalar()
        or 0
    )


def get_principal_for_school(db: Session, *, school_id: int) -> Principal | None:
    return db.query(Principal).filter(Principal.school_id == school_id).first()
