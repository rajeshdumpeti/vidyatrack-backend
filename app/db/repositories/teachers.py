from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models.class_ import Class
from app.db.models.section import Section
from app.db.models.section_subject_teacher import SectionSubjectTeacher
from app.db.models.subject import Subject
from app.db.models.teacher import Teacher
from app.db.models.teacher_primary_section import TeacherPrimarySection
from app.db.models.user import User
from app.db.models.user_school import UserSchool


def list_teachers_for_school(db: Session, *, school_id: int) -> list[Teacher]:
    """Return ALL teachers — used internally when building full TeacherOut objects."""
    return (
        db.query(Teacher)
        .filter(Teacher.school_id == school_id)
        .order_by(Teacher.id.asc())
        .all()
    )


def list_teachers_paginated(
    db: Session,
    *,
    school_id: int,
    search: str | None = None,
    page: int = 1,
    limit: int = 25,
) -> tuple[list[Teacher], int]:
    """Paginated teacher list with optional name search."""
    query = db.query(Teacher).filter(Teacher.school_id == school_id)
    if search:
        query = query.filter(Teacher.name.ilike(f"%{search}%"))
    total = query.count()
    items = query.order_by(Teacher.id.asc()).offset((page - 1) * limit).limit(limit).all()
    return items, total


def list_users_by_ids(db: Session, *, user_ids: list[int]) -> list[User]:
    if not user_ids:
        return []
    return db.query(User).filter(User.id.in_(user_ids)).all()


def list_primary_sections(
    db: Session,
    *,
    school_id: int,
    teacher_ids: list[int],
) -> list[tuple[int, str, str]]:
    if not teacher_ids:
        return []
    return (
        db.query(
            TeacherPrimarySection.teacher_id,
            Class.name.label("class_name"),
            Section.name.label("section_name"),
        )
        .join(Section, Section.id == TeacherPrimarySection.section_id)
        .join(Class, Class.id == Section.class_id)
        .filter(
            TeacherPrimarySection.school_id == school_id,
            TeacherPrimarySection.teacher_id.in_(teacher_ids),
        )
        .all()
    )


def list_assignment_rows(
    db: Session,
    *,
    school_id: int,
    teacher_ids: list[int],
) -> list[tuple[int, str, str, str]]:
    if not teacher_ids:
        return []
    return (
        db.query(
            SectionSubjectTeacher.teacher_id,
            Subject.name.label("subject_name"),
            Class.name.label("class_name"),
            Section.name.label("section_name"),
        )
        .join(Section, Section.id == SectionSubjectTeacher.section_id)
        .join(Class, Class.id == Section.class_id)
        .join(Subject, Subject.id == SectionSubjectTeacher.subject_id)
        .filter(
            SectionSubjectTeacher.school_id == school_id,
            SectionSubjectTeacher.teacher_id.in_(teacher_ids),
        )
        .all()
    )


def get_user_by_phone(db: Session, *, normalized_phone: str) -> User | None:
    return db.query(User).filter(User.phone == normalized_phone).first()


def get_teacher_by_school_and_user(
    db: Session,
    *,
    school_id: int,
    user_id: int,
) -> Teacher | None:
    return (
        db.query(Teacher)
        .filter(
            Teacher.school_id == school_id,
            Teacher.user_id == user_id,
        )
        .first()
    )


def get_user_school_link(
    db: Session,
    *,
    user_id: int,
    school_id: int,
) -> UserSchool | None:
    return (
        db.query(UserSchool)
        .filter(
            UserSchool.user_id == user_id,
            UserSchool.school_id == school_id,
        )
        .first()
    )
