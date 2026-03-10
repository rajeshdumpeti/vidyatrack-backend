from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v1.controllers import student_notes as student_notes_controller
from app.api.v1.deps import (
    get_db,
    get_current_user,
    require_teacher_or_management_or_principal,
    get_valid_school_id,
)
from app.api.v1.schemas.student_notes import StudentNoteCreate, StudentNoteOut
from app.db.models.user import User

router = APIRouter(prefix="/students", tags=["student-notes"])


@router.post("/{student_id}/notes", response_model=StudentNoteOut, status_code=201)
def create_student_note(
    student_id: str,
    payload: StudentNoteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_management_or_principal),
    school_id: int = Depends(get_valid_school_id),
) -> StudentNoteOut:
    return student_notes_controller.create_student_note(
        student_id=student_id,
        payload=payload,
        db=db,
        current_user=current_user,
        school_id=school_id,
    )


@router.get("/{student_id}/notes", response_model=list[StudentNoteOut])
def list_student_notes(
    student_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_management_or_principal),
    school_id: int = Depends(get_valid_school_id),
) -> list[StudentNoteOut]:
    return student_notes_controller.list_student_notes(
        student_id=student_id,
        db=db,
        school_id=school_id,
    )
