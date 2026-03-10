from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models.section_subject_teacher import SectionSubjectTeacher
from app.db.models.teacher_section_assignment import TeacherSectionAssignment


def list_teaching_assignments(
    db: Session,
    *,
    school_id: int,
    section_id: int | None,
    teacher_id: int | None,
) -> list[SectionSubjectTeacher]:
    query = db.query(SectionSubjectTeacher).filter(
        SectionSubjectTeacher.school_id == school_id
    )

    if section_id is not None:
        query = query.filter(SectionSubjectTeacher.section_id == section_id)

    if teacher_id is not None:
        query = query.filter(SectionSubjectTeacher.teacher_id == teacher_id)

    return query.order_by(SectionSubjectTeacher.id.asc()).all()


def list_teacher_section_assignments(
    db: Session,
    *,
    teacher_user_id: int,
    school_id: int,
) -> list[TeacherSectionAssignment]:
    return (
        db.query(TeacherSectionAssignment)
        .filter(
            TeacherSectionAssignment.teacher_user_id == teacher_user_id,
            TeacherSectionAssignment.school_id == school_id,
        )
        .all()
    )
