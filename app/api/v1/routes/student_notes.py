from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.api.v1.deps import (
    get_db,
    get_current_user,
    require_teacher_or_management_or_principal,
    get_valid_school_id
)
from app.db.models.principal import Principal
from app.db.models.teacher import Teacher
from app.db.models.user import User
from app.db.models.student import Student
from app.db.models.student_note import StudentNote

router = APIRouter(prefix="/students", tags=["student-notes"])

# --- SCHEMAS ---


class StudentNoteCreate(BaseModel):
    # Note: Only include note_text here. school_id comes from Query params.
    note_text: str
    model_config = ConfigDict(extra="forbid")


class StudentNoteOut(BaseModel):
    id: int
    school_id: int
    student_id: int
    author_user_id: int | None
    author_name: str | None = None
    author_role: str | None = None
    note_text: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# --- INTERNAL HELPERS ---


def _resolve_author_meta(db: Session, school_id: int, user_ids: set[int]):
    if not user_ids:
        return {}
    users = db.query(User).filter(User.id.in_(user_ids)).all()
    users_by_id = {u.id: u for u in users}
    teacher_user_ids = [u.id for u in users if u.role == "TEACHER"]
    principal_user_ids = [u.id for u in users if u.role == "PRINCIPAL"]

    teachers_by_user = {}
    if teacher_user_ids:
        teachers_by_user = {
            t.user_id: t for t in db.query(Teacher)
            .filter(Teacher.school_id == school_id, Teacher.user_id.in_(teacher_user_ids)).all()
        }
    principals_by_user = {}
    if principal_user_ids:
        principals_by_user = {
            p.user_id: p for p in db.query(Principal)
            .filter(Principal.school_id == school_id, Principal.user_id.in_(principal_user_ids)).all()
        }

    meta = {}
    for user_id, user in users_by_id.items():
        role = user.role
        name = "Management"
        if role == "TEACHER":
            name = teachers_by_user.get(
                user_id).name if teachers_by_user.get(user_id) else "Teacher"
        elif role == "PRINCIPAL":
            name = principals_by_user.get(
                user_id).name if principals_by_user.get(user_id) else "Principal"

        meta[user_id] = {"name": name, "role": role.lower() if role else None}
    return meta

# --- ROUTES ---


@router.post("/{student_id}/notes", response_model=StudentNoteOut, status_code=201)
def create_student_note(
    student_id: int,
    payload: StudentNoteCreate,
    db: Session = Depends(get_db),
    # Returns User object: access via current_user.id
    current_user: User = Depends(require_teacher_or_management_or_principal),
    # Captures ?school_id=15 from your frontend request
    school_id: int = Depends(get_valid_school_id),
):
    if not payload.note_text.strip():
        raise HTTPException(status_code=422, detail="note_text_required")

    student = db.query(Student).filter(
        Student.id == student_id,
        Student.school_id == school_id
    ).first()

    if not student:
        raise HTTPException(status_code=400, detail="invalid_student_id")

    note = StudentNote(
        school_id=school_id,
        student_id=student_id,
        author_user_id=current_user.id,  # FIXED: dot notation, not brackets
        note_text=payload.note_text,
    )
    db.add(note)
    db.commit()
    db.refresh(note)

    meta = _resolve_author_meta(db, school_id, {current_user.id})
    author = meta.get(current_user.id, {})

    return StudentNoteOut(
        id=note.id,
        school_id=note.school_id,
        student_id=note.student_id,
        author_user_id=note.author_user_id,
        author_name=author.get("name"),
        author_role=author.get("role"),
        note_text=note.note_text,
        created_at=note.created_at,
    )


@router.get("/{student_id}/notes", response_model=list[StudentNoteOut])
def list_student_notes(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_management_or_principal),
    school_id: int = Depends(get_valid_school_id),
):
    student = db.query(Student).filter(
        Student.id == student_id,
        Student.school_id == school_id
    ).first()

    if not student:
        raise HTTPException(status_code=400, detail="invalid_student_id")

    notes = db.query(StudentNote).filter(
        StudentNote.school_id == school_id,
        StudentNote.student_id == student_id,
    ).order_by(StudentNote.created_at.desc()).all()

    author_ids = {n.author_user_id for n in notes if n.author_user_id}
    meta = _resolve_author_meta(db, school_id, author_ids)

    return [
        StudentNoteOut(
            id=n.id,
            school_id=n.school_id,
            student_id=n.student_id,
            author_user_id=n.author_user_id,
            author_name=meta.get(n.author_user_id, {}).get("name"),
            author_role=meta.get(n.author_user_id, {}).get("role"),
            note_text=n.note_text,
            created_at=n.created_at,
        ) for n in notes
    ]
