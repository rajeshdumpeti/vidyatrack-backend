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
from app.db.models.section_subject_teacher import SectionSubjectTeacher
from app.db.models.section import Section
from app.db.models.class_ import Class
from app.db.models.subject import Subject

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
    class_name: str | None = None
    section_name: str | None = None
    subject_name: str | None = None
    note_text: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# --- INTERNAL HELPERS ---


def _resolve_author_meta(
    db: Session,
    school_id: int,
    user_ids: set[int],
    student_section_id: int | None = None,
):
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

    teacher_assignment_meta: dict[int, dict[str, str | None]] = {}
    teacher_ids = [t.id for t in teachers_by_user.values()]
    if teacher_ids:
        assignment_q = (
            db.query(
                SectionSubjectTeacher.teacher_id.label("teacher_id"),
                Class.name.label("class_name"),
                Section.name.label("section_name"),
                Subject.name.label("subject_name"),
            )
            .join(Section, Section.id == SectionSubjectTeacher.section_id)
            .join(Class, Class.id == Section.class_id)
            .join(Subject, Subject.id == SectionSubjectTeacher.subject_id)
            .filter(
                SectionSubjectTeacher.school_id == school_id,
                SectionSubjectTeacher.teacher_id.in_(teacher_ids),
            )
        )
        if student_section_id is not None:
            assignment_q = assignment_q.filter(
                SectionSubjectTeacher.section_id == student_section_id
            )

        grouped: dict[int, dict[str, set[str]]] = {}
        for row in assignment_q.all():
            bucket = grouped.setdefault(
                row.teacher_id,
                {"class_names": set(), "section_names": set(), "subject_names": set()},
            )
            if row.class_name:
                bucket["class_names"].add(row.class_name)
            if row.section_name:
                bucket["section_names"].add(row.section_name)
            if row.subject_name:
                bucket["subject_names"].add(row.subject_name)

        for teacher_id, bucket in grouped.items():
            teacher_assignment_meta[teacher_id] = {
                "class_name": ", ".join(sorted(bucket["class_names"])) if bucket["class_names"] else None,
                "section_name": ", ".join(sorted(bucket["section_names"])) if bucket["section_names"] else None,
                "subject_name": ", ".join(sorted(bucket["subject_names"])) if bucket["subject_names"] else None,
            }

    meta = {}
    for user_id, user in users_by_id.items():
        role = user.role
        name = "Management"
        class_name = None
        section_name = None
        subject_name = None
        if role == "TEACHER":
            teacher = teachers_by_user.get(user_id)
            name = teacher.name if teacher else "Teacher"
            if teacher:
                assignment_meta = teacher_assignment_meta.get(teacher.id, {})
                class_name = assignment_meta.get("class_name")
                section_name = assignment_meta.get("section_name")
                subject_name = assignment_meta.get("subject_name")
        elif role == "PRINCIPAL":
            name = principals_by_user.get(
                user_id).name if principals_by_user.get(user_id) else "Principal"

        meta[user_id] = {
            "name": name,
            "role": role.lower() if role else None,
            "class_name": class_name,
            "section_name": section_name,
            "subject_name": subject_name,
        }
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

    meta = _resolve_author_meta(
        db, school_id, {current_user.id}, student.section_id
    )
    author = meta.get(current_user.id, {})

    return StudentNoteOut(
        id=note.id,
        school_id=note.school_id,
        student_id=note.student_id,
        author_user_id=note.author_user_id,
        author_name=author.get("name"),
        author_role=author.get("role"),
        class_name=author.get("class_name"),
        section_name=author.get("section_name"),
        subject_name=author.get("subject_name"),
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
    meta = _resolve_author_meta(db, school_id, author_ids, student.section_id)

    return [
        StudentNoteOut(
            id=n.id,
            school_id=n.school_id,
            student_id=n.student_id,
            author_user_id=n.author_user_id,
            author_name=meta.get(n.author_user_id, {}).get("name"),
            author_role=meta.get(n.author_user_id, {}).get("role"),
            class_name=meta.get(n.author_user_id, {}).get("class_name"),
            section_name=meta.get(n.author_user_id, {}).get("section_name"),
            subject_name=meta.get(n.author_user_id, {}).get("subject_name"),
            note_text=n.note_text,
            created_at=n.created_at,
        ) for n in notes
    ]
