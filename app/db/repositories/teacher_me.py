from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models.class_ import Class
from app.db.models.section import Section
from app.db.models.teacher import Teacher
from app.db.models.teacher_primary_section import TeacherPrimarySection


def get_teacher_by_user_id(db: Session, *, user_id: int) -> Teacher | None:
    return db.query(Teacher).filter(Teacher.user_id == user_id).first()


def get_primary_section_mapping(
    db: Session,
    *,
    school_id: int,
    teacher_id: int,
) -> TeacherPrimarySection | None:
    return (
        db.query(TeacherPrimarySection)
        .filter(
            TeacherPrimarySection.school_id == school_id,
            TeacherPrimarySection.teacher_id == teacher_id,
        )
        .first()
    )


def get_section(db: Session, *, school_id: int, section_id: int) -> Section | None:
    return (
        db.query(Section)
        .filter(
            Section.school_id == school_id,
            Section.id == section_id,
        )
        .first()
    )


def get_class_for_section(
    db: Session,
    *,
    school_id: int,
    class_id: int,
) -> Class | None:
    return (
        db.query(Class)
        .filter(
            Class.school_id == school_id,
            Class.id == class_id,
        )
        .first()
    )
