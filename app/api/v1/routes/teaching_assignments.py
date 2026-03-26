from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.v1.controllers import teaching_assignments as teaching_assignments_controller
from app.api.v1.deps import get_current_user, get_db, get_valid_school_id, require_management
from app.api.v1.schemas.teaching_assignments import (
    SetSubstitutePayload,
    TeacherAssignmentHistoryOut,
    TeachingAssignmentCreate,
    TeachingAssignmentOut,
)
from app.db.models.section_subject_teacher import SectionSubjectTeacher
from app.db.models.teacher_assignment_history import TeacherAssignmentHistory
from app.db.models.user import User

router = APIRouter(prefix="/teaching-assignments",
                   tags=["teaching-assignments"])


@router.post("", response_model=TeachingAssignmentOut, status_code=201)
def create_teaching_assignment(
    payload: TeachingAssignmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_management),
) -> SectionSubjectTeacher:
    return teaching_assignments_controller.create_teaching_assignment(
        db=db,
        payload=payload,
        changed_by_user_id=current_user.id,
    )


@router.get("/history", response_model=List[TeacherAssignmentHistoryOut])
def get_assignment_history(
    school_id: int,
    section_id: int,
    subject_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_management),
) -> list[TeacherAssignmentHistory]:
    return teaching_assignments_controller.list_assignment_history(
        db=db,
        school_id=school_id,
        section_id=section_id,
        subject_id=subject_id,
    )


@router.get("", response_model=List[TeachingAssignmentOut])
def list_teaching_assignments(
    school_id: int,
    section_id: int | None = Query(None),
    teacher_id: int | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[SectionSubjectTeacher]:
    return teaching_assignments_controller.list_teaching_assignments(
        db=db,
        school_id=school_id,
        section_id=section_id,
        teacher_id=teacher_id,
    )


@router.patch("/{assignment_id}/substitute", response_model=TeachingAssignmentOut)
def set_substitute_teacher(
    assignment_id: int,
    payload: SetSubstitutePayload,
    school_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_management),
) -> SectionSubjectTeacher:
    return teaching_assignments_controller.set_substitute_teacher(
        db=db,
        assignment_id=assignment_id,
        school_id=school_id,
        substitute_teacher_id=payload.substitute_teacher_id,
    )


@router.get("/my-sections")
def get_my_sections(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    school_id: int = Depends(get_valid_school_id),
) -> list[dict]:
    return teaching_assignments_controller.get_my_sections(
        db=db,
        teacher_user_id=current_user.id,
        school_id=school_id,
    )
