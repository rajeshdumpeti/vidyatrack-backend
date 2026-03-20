from __future__ import annotations

from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.api.v1.schemas.student_notes import StudentNoteCreate, StudentNoteOut
from app.core.roles import normalize_role
from app.db.models.class_ import Class
from app.db.models.principal import Principal
from app.db.models.section import Section
from app.db.models.section_subject_teacher import SectionSubjectTeacher
from app.db.models.student import Student
from app.db.models.student_note import StudentNote
from app.db.models.subject import Subject
from app.db.models.teacher import Teacher
from app.db.models.user import User


def _resolve_author_meta(
    db: Session,
    school_id: int,
    user_ids: set[int],
    student_section_id: int | None = None,
) -> dict[int, dict[str, str | None]]:
    if not user_ids:
        return {}
    users = db.query(User).filter(User.id.in_(user_ids)).all()
    users_by_id = {user.id: user for user in users}
    teacher_user_ids = [user.id for user in users if normalize_role(user.role) == "TEACHER"]
    principal_user_ids = [user.id for user in users if normalize_role(user.role) == "PRINCIPAL"]

    teachers_by_user = {}
    if teacher_user_ids:
        teachers_by_user = {
            teacher.user_id: teacher
            for teacher in db.query(Teacher)
            .filter(Teacher.school_id == school_id, Teacher.user_id.in_(teacher_user_ids))
            .all()
        }

    principals_by_user = {}
    if principal_user_ids:
        principals_by_user = {
            principal.user_id: principal
            for principal in db.query(Principal)
            .filter(Principal.school_id == school_id, Principal.user_id.in_(principal_user_ids))
            .all()
        }

    teacher_assignment_meta: dict[int, dict[str, str | None]] = {}
    teacher_ids = [teacher.id for teacher in teachers_by_user.values()]
    if teacher_ids:
        assignment_query = (
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
            assignment_query = assignment_query.filter(
                SectionSubjectTeacher.section_id == student_section_id
            )

        grouped: dict[int, dict[str, set[str]]] = {}
        for row in assignment_query.all():
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

    meta: dict[int, dict[str, str | None]] = {}
    for user_id, user in users_by_id.items():
        role = normalize_role(user.role)
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
            name = principals_by_user.get(user_id).name if principals_by_user.get(user_id) else "Principal"

        meta[user_id] = {
            "name": name,
            "role": role.lower() if role else None,
            "class_name": class_name,
            "section_name": section_name,
            "subject_name": subject_name,
        }
    return meta


def _resolve_student_by_ref(db: Session, school_id: int, student_ref: str) -> Student | None:
    if student_ref.isdigit():
        return (
            db.query(Student)
            .filter(Student.id == int(student_ref), Student.school_id == school_id)
            .first()
        )
    return (
        db.query(Student)
        .filter(Student.public_id == student_ref, Student.school_id == school_id)
        .first()
    )


def _resolve_student_section_meta(
    db: Session,
    school_id: int,
    section_id: int | None,
) -> tuple[str | None, str | None]:
    if section_id is None:
        return None, None
    row = (
        db.query(Section, Class)
        .join(Class, Class.id == Section.class_id)
        .filter(Section.id == section_id, Section.school_id == school_id)
        .first()
    )
    if not row:
        return None, None
    section, class_ = row
    return class_.name, section.name


def create_student_note(
    *,
    student_id: str,
    payload: StudentNoteCreate,
    db: Session,
    current_user: User,
    school_id: int,
) -> StudentNoteOut:
    if not payload.note_text.strip():
        raise HTTPException(status_code=422, detail="note_text_required")

    student = _resolve_student_by_ref(db, school_id, student_id)
    if not student:
        raise HTTPException(status_code=400, detail="invalid_student_id")

    if payload.section_id is not None:
        section = (
            db.query(Section.id)
            .filter(Section.school_id == school_id, Section.id == payload.section_id)
            .first()
        )
        if not section:
            raise HTTPException(status_code=400, detail="invalid_section_id")
    if payload.subject_id is not None:
        subject = (
            db.query(Subject.id)
            .filter(Subject.school_id == school_id, Subject.id == payload.subject_id)
            .first()
        )
        if not subject:
            raise HTTPException(status_code=400, detail="invalid_subject_id")

    note = StudentNote(
        school_id=school_id,
        student_id=student.id,
        section_id=payload.section_id,
        subject_id=payload.subject_id,
        author_user_id=current_user.id,
        note_text=payload.note_text,
    )
    db.add(note)
    db.commit()
    db.refresh(note)

    meta = _resolve_author_meta(db, school_id, {current_user.id}, student.section_id)
    author = meta.get(current_user.id, {})
    class_name = author.get("class_name")
    section_name = author.get("section_name")
    subject_name = author.get("subject_name")
    if note.section_id:
        class_name, section_name = _resolve_student_section_meta(db, school_id, note.section_id)
    else:
        fallback_class, fallback_section = _resolve_student_section_meta(db, school_id, student.section_id)
        class_name = class_name or fallback_class
        section_name = section_name or fallback_section
    if note.subject_id:
        subject_row = (
            db.query(Subject.name)
            .filter(Subject.id == note.subject_id, Subject.school_id == school_id)
            .first()
        )
        if subject_row:
            subject_name = subject_row[0]

    return StudentNoteOut(
        id=note.id,
        school_id=note.school_id,
        student_id=note.student_id,
        student_name=student.name,
        section_id=note.section_id,
        subject_id=note.subject_id,
        author_user_id=note.author_user_id,
        author_name=author.get("name"),
        author_role=author.get("role"),
        class_name=class_name,
        section_name=section_name,
        subject_name=subject_name,
        note_text=note.note_text,
        created_at=note.created_at,
    )


def list_student_notes(
    *,
    student_id: str,
    db: Session,
    school_id: int,
) -> list[StudentNoteOut]:
    student = _resolve_student_by_ref(db, school_id, student_id)
    if not student:
        raise HTTPException(status_code=400, detail="invalid_student_id")

    notes = (
        db.query(StudentNote)
        .filter(
            StudentNote.school_id == school_id,
            StudentNote.student_id == student.id,
        )
        .order_by(StudentNote.created_at.desc())
        .all()
    )

    author_ids = {note.author_user_id for note in notes if note.author_user_id}
    meta = _resolve_author_meta(db, school_id, author_ids, student.section_id)

    section_ids = {note.section_id for note in notes if note.section_id}
    if student.section_id:
        section_ids.add(student.section_id)
    subject_ids = {note.subject_id for note in notes if note.subject_id}

    sections_by_id = {}
    subjects_by_id = {}
    if section_ids:
        section_rows = (
            db.query(Section, Class)
            .join(Class, Class.id == Section.class_id)
            .filter(Section.id.in_(section_ids), Section.school_id == school_id)
            .all()
        )
        sections_by_id = {
            section.id: {"section": section.name, "class": class_.name}
            for section, class_ in section_rows
        }
    if subject_ids:
        subject_rows = (
            db.query(Subject.id, Subject.name)
            .filter(Subject.id.in_(subject_ids), Subject.school_id == school_id)
            .all()
        )
        subjects_by_id = {subject_id: name for subject_id, name in subject_rows}

    return [
        StudentNoteOut(
            id=note.id,
            school_id=note.school_id,
            student_id=note.student_id,
            student_name=student.name,
            section_id=note.section_id,
            subject_id=note.subject_id,
            author_user_id=note.author_user_id,
            author_name=meta.get(note.author_user_id, {}).get("name"),
            author_role=meta.get(note.author_user_id, {}).get("role"),
            class_name=sections_by_id.get(note.section_id, {}).get("class")
            if note.section_id
            else sections_by_id.get(student.section_id, {}).get("class")
            or meta.get(note.author_user_id, {}).get("class_name"),
            section_name=sections_by_id.get(note.section_id, {}).get("section")
            if note.section_id
            else sections_by_id.get(student.section_id, {}).get("section")
            or meta.get(note.author_user_id, {}).get("section_name"),
            subject_name=subjects_by_id.get(note.subject_id)
            if note.subject_id
            else meta.get(note.author_user_id, {}).get("subject_name"),
            note_text=note.note_text,
            created_at=note.created_at,
        )
        for note in notes
    ]
