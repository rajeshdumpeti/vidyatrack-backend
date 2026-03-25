from sqlalchemy.orm import Session

from app.api.v1.schemas.teaching_assignments import TeachingAssignmentCreate
from app.db.models.section_subject_teacher import SectionSubjectTeacher
from app.db.repositories import teaching_assignments as teaching_assignments_repository


def create_teaching_assignment(
    *,
    db: Session,
    payload: TeachingAssignmentCreate,
) -> SectionSubjectTeacher:
    existing = teaching_assignments_repository.get_teaching_assignment(
        db,
        school_id=payload.school_id,
        section_id=payload.section_id,
        subject_id=payload.subject_id,
    )
    if existing:
        existing.teacher_id = payload.teacher_id
        db.commit()
        db.refresh(existing)
        return existing

    new_assignment = SectionSubjectTeacher(
        school_id=payload.school_id,
        section_id=payload.section_id,
        subject_id=payload.subject_id,
        teacher_id=payload.teacher_id,
    )
    db.add(new_assignment)
    db.commit()
    db.refresh(new_assignment)
    return new_assignment


def list_teaching_assignments(
    *,
    db: Session,
    school_id: int,
    section_id: int | None,
    teacher_id: int | None,
) -> list[SectionSubjectTeacher]:
    return teaching_assignments_repository.list_teaching_assignments(
        db,
        school_id=school_id,
        section_id=section_id,
        teacher_id=teacher_id,
    )


def get_my_sections(*, db: Session, teacher_user_id: int, school_id: int) -> list[dict]:
    assignments = teaching_assignments_repository.list_teacher_section_assignments(
        db,
        teacher_user_id=teacher_user_id,
        school_id=school_id,
    )
    return [
        {
            "section_id": assignment.section_id,
            "subject_name": assignment.subject_name,
            "is_primary": assignment.is_primary_teacher,
        }
        for assignment in assignments
    ]
