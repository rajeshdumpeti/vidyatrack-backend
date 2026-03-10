from sqlalchemy.orm import Session

from app.api.v1.schemas.teaching_assignments import TeachingAssignmentCreate
from app.db.models.section_subject_teacher import SectionSubjectTeacher
from app.services.teaching_assignments import (
    create_teaching_assignment as create_teaching_assignment_service,
)
from app.services.teaching_assignments import get_my_sections as get_my_sections_service
from app.services.teaching_assignments import (
    list_teaching_assignments as list_teaching_assignments_service,
)


def create_teaching_assignment(
    *,
    db: Session,
    payload: TeachingAssignmentCreate,
) -> SectionSubjectTeacher:
    return create_teaching_assignment_service(db=db, payload=payload)


def list_teaching_assignments(
    *,
    db: Session,
    school_id: int,
    section_id: int | None,
    teacher_id: int | None,
) -> list[SectionSubjectTeacher]:
    return list_teaching_assignments_service(
        db=db,
        school_id=school_id,
        section_id=section_id,
        teacher_id=teacher_id,
    )


def get_my_sections(*, db: Session, teacher_user_id: int, school_id: int) -> list[dict]:
    return get_my_sections_service(
        db=db,
        teacher_user_id=teacher_user_id,
        school_id=school_id,
    )
