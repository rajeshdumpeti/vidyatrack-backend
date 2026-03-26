from sqlalchemy.orm import Session

from app.api.v1.schemas.teaching_assignments import TeachingAssignmentCreate
from app.db.models.section_subject_teacher import SectionSubjectTeacher
from app.db.models.teacher_assignment_history import TeacherAssignmentHistory
from app.services.teaching_assignments import (
    create_teaching_assignment as create_teaching_assignment_service,
)
from app.services.teaching_assignments import get_my_sections as get_my_sections_service
from app.services.teaching_assignments import (
    list_assignment_history as list_assignment_history_service,
)
from app.services.teaching_assignments import (
    list_teaching_assignments as list_teaching_assignments_service,
)
from app.services.teaching_assignments import (
    set_substitute_teacher as set_substitute_teacher_service,
)


def create_teaching_assignment(
    *,
    db: Session,
    payload: TeachingAssignmentCreate,
    changed_by_user_id: int | None = None,
) -> SectionSubjectTeacher:
    return create_teaching_assignment_service(
        db=db, payload=payload, changed_by_user_id=changed_by_user_id
    )


def list_assignment_history(
    *,
    db: Session,
    school_id: int,
    section_id: int,
    subject_id: int,
) -> list[TeacherAssignmentHistory]:
    return list_assignment_history_service(
        db=db,
        school_id=school_id,
        section_id=section_id,
        subject_id=subject_id,
    )


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


def set_substitute_teacher(
    *,
    db: Session,
    assignment_id: int,
    school_id: int,
    substitute_teacher_id: int | None,
) -> SectionSubjectTeacher:
    return set_substitute_teacher_service(
        db=db,
        assignment_id=assignment_id,
        school_id=school_id,
        substitute_teacher_id=substitute_teacher_id,
    )


def get_my_sections(*, db: Session, teacher_user_id: int, school_id: int) -> list[dict]:
    return get_my_sections_service(
        db=db,
        teacher_user_id=teacher_user_id,
        school_id=school_id,
    )
