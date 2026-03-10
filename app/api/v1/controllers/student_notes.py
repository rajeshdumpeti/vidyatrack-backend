from sqlalchemy.orm import Session

from app.api.v1.schemas.student_notes import StudentNoteCreate, StudentNoteOut
from app.db.models.user import User
from app.services import student_notes as student_notes_service


def create_student_note(
    *,
    student_id: str,
    payload: StudentNoteCreate,
    db: Session,
    current_user: User,
    school_id: int,
) -> StudentNoteOut:
    return student_notes_service.create_student_note(
        student_id=student_id,
        payload=payload,
        db=db,
        current_user=current_user,
        school_id=school_id,
    )


def list_student_notes(
    *,
    student_id: str,
    db: Session,
    school_id: int,
) -> list[StudentNoteOut]:
    return student_notes_service.list_student_notes(
        student_id=student_id,
        db=db,
        school_id=school_id,
    )
