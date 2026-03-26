from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models.section_subject_teacher import SectionSubjectTeacher
from app.db.models.teacher_assignment_history import TeacherAssignmentHistory
from app.db.models.teacher_section_assignment import TeacherSectionAssignment


def get_teaching_assignment(
    db: Session,
    *,
    school_id: int,
    section_id: int,
    subject_id: int,
) -> SectionSubjectTeacher | None:
    return (
        db.query(SectionSubjectTeacher)
        .filter(
            SectionSubjectTeacher.school_id == school_id,
            SectionSubjectTeacher.section_id == section_id,
            SectionSubjectTeacher.subject_id == subject_id,
        )
        .first()
    )


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


def create_assignment_history(
    db: Session,
    *,
    school_id: int,
    section_id: int,
    subject_id: int,
    previous_teacher_id: int | None,
    new_teacher_id: int,
    changed_by_user_id: int | None,
    action: str,
) -> TeacherAssignmentHistory:
    record = TeacherAssignmentHistory(
        school_id=school_id,
        section_id=section_id,
        subject_id=subject_id,
        previous_teacher_id=previous_teacher_id,
        new_teacher_id=new_teacher_id,
        changed_by_user_id=changed_by_user_id,
        action=action,
    )
    db.add(record)
    return record


def list_assignment_history(
    db: Session,
    *,
    school_id: int,
    section_id: int,
    subject_id: int,
) -> list[TeacherAssignmentHistory]:
    return (
        db.query(TeacherAssignmentHistory)
        .filter(
            TeacherAssignmentHistory.school_id == school_id,
            TeacherAssignmentHistory.section_id == section_id,
            TeacherAssignmentHistory.subject_id == subject_id,
        )
        .order_by(TeacherAssignmentHistory.changed_at.desc())
        .all()
    )


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
