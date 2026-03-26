from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.api.v1.schemas.teaching_assignments import TeachingAssignmentCreate
from app.db.models.section_subject_teacher import SectionSubjectTeacher
from app.db.models.teacher import Teacher
from app.db.models.teacher_assignment_history import TeacherAssignmentHistory
from app.db.repositories import teaching_assignments as teaching_assignments_repository


def create_teaching_assignment(
    *,
    db: Session,
    payload: TeachingAssignmentCreate,
    changed_by_user_id: int | None = None,
) -> SectionSubjectTeacher:
    # Block assignment of non-ACTIVE teachers
    teacher = db.query(Teacher).filter(Teacher.id == payload.teacher_id).first()
    if teacher and teacher.status != "ACTIVE":
        status_label = teacher.status.replace("_", " ").title()
        raise HTTPException(
            status_code=400,
            detail=f"Cannot assign teacher — current status is {status_label}. "
                   "Only ACTIVE teachers can be assigned to subjects.",
        )

    existing = teaching_assignments_repository.get_teaching_assignment(
        db,
        school_id=payload.school_id,
        section_id=payload.section_id,
        subject_id=payload.subject_id,
    )
    if existing:
        previous_teacher_id = existing.teacher_id
        existing.teacher_id = payload.teacher_id
        teaching_assignments_repository.create_assignment_history(
            db,
            school_id=payload.school_id,
            section_id=payload.section_id,
            subject_id=payload.subject_id,
            previous_teacher_id=previous_teacher_id,
            new_teacher_id=payload.teacher_id,
            changed_by_user_id=changed_by_user_id,
            action="REASSIGNED",
        )
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
    teaching_assignments_repository.create_assignment_history(
        db,
        school_id=payload.school_id,
        section_id=payload.section_id,
        subject_id=payload.subject_id,
        previous_teacher_id=None,
        new_teacher_id=payload.teacher_id,
        changed_by_user_id=changed_by_user_id,
        action="ASSIGNED",
    )
    db.commit()
    db.refresh(new_assignment)
    return new_assignment


def list_assignment_history(
    *,
    db: Session,
    school_id: int,
    section_id: int,
    subject_id: int,
) -> list[TeacherAssignmentHistory]:
    return teaching_assignments_repository.list_assignment_history(
        db,
        school_id=school_id,
        section_id=section_id,
        subject_id=subject_id,
    )


def set_substitute_teacher(
    *,
    db: Session,
    assignment_id: int,
    school_id: int,
    substitute_teacher_id: int | None,
) -> SectionSubjectTeacher:
    assignment = (
        db.query(SectionSubjectTeacher)
        .filter(
            SectionSubjectTeacher.id == assignment_id,
            SectionSubjectTeacher.school_id == school_id,
        )
        .first()
    )
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found.")

    if substitute_teacher_id is not None:
        sub = db.query(Teacher).filter(Teacher.id == substitute_teacher_id).first()
        if not sub:
            raise HTTPException(status_code=404, detail="Substitute teacher not found.")
        if sub.status != "ACTIVE":
            status_label = sub.status.replace("_", " ").title()
            raise HTTPException(
                status_code=400,
                detail=f"Substitute must be ACTIVE — current status is {status_label}.",
            )

    assignment.substitute_teacher_id = substitute_teacher_id
    db.commit()
    db.refresh(assignment)
    return assignment


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
