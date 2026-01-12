from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.api.v1.deps import get_db, get_current_user, require_teacher_or_management_or_principal
from app.db.models.student import Student
from app.db.models.student_note import StudentNote

router = APIRouter(prefix="/students", tags=["student-notes"])


class StudentNoteCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    note_text: str


class StudentNoteOut(BaseModel):
    id: int
    school_id: int
    student_id: int
    author_user_id: int | None
    note_text: str
    created_at: datetime  # Changed from str to datetime

    class Config:
        from_attributes = True


@router.post("/{student_id}/notes", response_model=StudentNoteOut, status_code=201)
def create_student_note(
    student_id: int,
    payload: StudentNoteCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_teacher_or_management_or_principal),
):
    if not payload.note_text.strip():
        raise HTTPException(status_code=422, detail="note_text_required")

    student = (
        db.query(Student)
        .filter(
            Student.id == student_id,
            Student.school_id == current_user["school_id"],
        )
        .first()
    )
    if not student:
        raise HTTPException(status_code=400, detail="invalid_student_id")

    note = StudentNote(
        school_id=current_user["school_id"],
        student_id=student_id,
        author_user_id=current_user["user_id"],
        note_text=payload.note_text,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


@router.get("/{student_id}/notes", response_model=list[StudentNoteOut])
def list_student_notes(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_teacher_or_management_or_principal),
):
    student = (
        db.query(Student)
        .filter(
            Student.id == student_id,
            Student.school_id == current_user["school_id"],
        )
        .first()
    )
    if not student:
        raise HTTPException(status_code=400, detail="invalid_student_id")

    return (
        db.query(StudentNote)
        .filter(
            StudentNote.school_id == current_user["school_id"],
            StudentNote.student_id == student_id,
        )
        .order_by(StudentNote.created_at.desc())
        .all()
    )
