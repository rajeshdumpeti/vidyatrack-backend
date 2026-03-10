from __future__ import annotations
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v1.controllers import teachers_me as teachers_me_controller
from app.api.v1.deps import get_db, get_valid_school_id, require_teacher
from app.api.v1.schemas.teachers_me import (
    TeacherAttendanceSectionOut,
    TeacherContextOut,
    TeacherMeOut,
    TeacherReadinessOut,
    TeachingAssignmentOut,
)
from app.db.models.user import User

router = APIRouter(prefix="/teachers/me", tags=["teachers-me"])


@router.get("", response_model=TeacherMeOut)
def get_my_teacher_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher),
) -> TeacherMeOut:
    return teachers_me_controller.get_my_teacher_profile(db=db, current_user=current_user)


@router.get("/context", response_model=TeacherContextOut)
def get_my_teacher_context(
    db: Session = Depends(get_db),
    school_id: int = Depends(get_valid_school_id),
    current_user: User = Depends(require_teacher),
) -> TeacherContextOut:
    return teachers_me_controller.get_my_teacher_context(
        db=db,
        school_id=school_id,
        current_user=current_user,
    )


@router.get("/teaching-assignments", response_model=list[TeachingAssignmentOut])
def get_my_teaching_assignments(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher),
) -> list[TeachingAssignmentOut]:
    return teachers_me_controller.get_my_teaching_assignments(db=db, current_user=current_user)


@router.get("/attendance-section", response_model=TeacherAttendanceSectionOut)
def get_my_attendance_section(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher),
) -> TeacherAttendanceSectionOut:
    return teachers_me_controller.get_my_attendance_section(db=db, current_user=current_user)


@router.get("/readiness", response_model=TeacherReadinessOut)
def get_my_teacher_readiness(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher),
) -> TeacherReadinessOut:
    return teachers_me_controller.get_my_teacher_readiness(db=db, current_user=current_user)
