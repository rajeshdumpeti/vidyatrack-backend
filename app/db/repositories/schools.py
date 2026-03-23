from __future__ import annotations

from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models.management_admin import ManagementAdmin
from app.db.models.principal import Principal
from app.db.models.school import School
from app.db.models.student import Student
from app.db.models.teacher import Teacher
from app.db.models.user import User
from app.db.models.user_school import UserSchool


def get_school_by_id(db: Session, school_id: int) -> School | None:
    return db.query(School).filter(School.id == school_id).first()


def list_schools(
    db: Session,
    *,
    search: Optional[str] = None,
    page: int = 1,
    limit: int = 25,
) -> tuple[list[School], int]:
    q = db.query(School)
    if search:
        pattern = f"%{search}%"
        q = q.filter(School.name.ilike(pattern))
    total = q.count()
    items = q.order_by(School.id.asc()).offset((page - 1) * limit).limit(limit).all()
    return items, total


def list_school_teachers_paginated(
    db: Session, *, school_id: int, page: int = 1, limit: int = 25
) -> tuple[list[tuple], int]:
    q = (
        db.query(Teacher, User)
        .outerjoin(User, Teacher.user_id == User.id)
        .filter(Teacher.school_id == school_id)
        .order_by(Teacher.id.asc())
    )
    total = q.count()
    items = q.offset((page - 1) * limit).limit(limit).all()
    return items, total


def list_school_students_paginated(
    db: Session, *, school_id: int, page: int = 1, limit: int = 25
) -> tuple[list[Student], int]:
    q = db.query(Student).filter(Student.school_id == school_id).order_by(Student.id.asc())
    total = q.count()
    items = q.offset((page - 1) * limit).limit(limit).all()
    return items, total


def list_school_staff_paginated(
    db: Session, *, school_id: int, page: int = 1, limit: int = 25
) -> tuple[list[tuple], int]:
    q = (
        db.query(UserSchool, User, Principal, ManagementAdmin)
        .join(User, UserSchool.user_id == User.id)
        .outerjoin(
            Principal,
            (Principal.user_id == User.id) & (Principal.school_id == school_id),
        )
        .outerjoin(
            ManagementAdmin,
            (ManagementAdmin.user_id == User.id) & (ManagementAdmin.school_id == school_id),
        )
        .filter(
            UserSchool.school_id == school_id,
            func.lower(UserSchool.role).notin_(["teacher", "student"]),
        )
        .order_by(UserSchool.id.asc())
    )
    total = q.count()
    items = q.offset((page - 1) * limit).limit(limit).all()
    return items, total


def count_user_school_role(db: Session, *, school_id: int, role: str) -> int:
    return (
        db.query(UserSchool)
        .filter(
            UserSchool.school_id == school_id,
            UserSchool.role == role,
        )
        .count()
    )


def count_teachers(db: Session, *, school_id: int) -> int:
    return db.query(func.count(Teacher.id)).filter(Teacher.school_id == school_id).scalar() or 0


def count_students(db: Session, *, school_id: int) -> int:
    return db.query(func.count(Student.id)).filter(Student.school_id == school_id).scalar() or 0


def count_staff(db: Session, *, school_id: int) -> int:
    return (
        db.query(func.count(UserSchool.id))
        .filter(
            UserSchool.school_id == school_id,
            func.lower(UserSchool.role).notin_(["teacher", "student"]),
        )
        .scalar()
        or 0
    )


def list_school_teachers(db: Session, *, school_id: int) -> list[tuple[Teacher, User | None]]:
    return (
        db.query(Teacher, User)
        .outerjoin(User, Teacher.user_id == User.id)
        .filter(Teacher.school_id == school_id)
        .order_by(Teacher.id.asc())
        .all()
    )


def list_school_students(db: Session, *, school_id: int) -> list[Student]:
    return (
        db.query(Student)
        .filter(Student.school_id == school_id)
        .order_by(Student.id.asc())
        .all()
    )


def list_school_staff(db: Session, *, school_id: int) -> list[tuple[UserSchool, User]]:
    return (
        db.query(UserSchool, User)
        .join(User, UserSchool.user_id == User.id)
        .filter(
            UserSchool.school_id == school_id,
            func.lower(UserSchool.role).notin_(["teacher", "student"]),
        )
        .order_by(UserSchool.id.asc())
        .all()
    )


def get_user_by_phone(db: Session, *, phone: str) -> User | None:
    return db.query(User).filter(User.phone == phone).first()

