from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models.attendance_record import AttendanceRecord
from app.db.models.class_ import Class
from app.db.models.marks_record import MarksRecord
from app.db.models.section import Section
from app.db.models.student import Student
from app.db.models.student_import_batch import StudentImportBatch
from app.db.models.subject import Subject


def list_students_with_sections(
    db: Session,
    *,
    school_id: int,
    section_id: int | None,
) -> list[tuple[Student, Section | None, Class | None]]:
    query = (
        db.query(Student, Section, Class)
        .outerjoin(Section, Section.id == Student.section_id)
        .outerjoin(Class, Class.id == Section.class_id)
        .filter(Student.school_id == school_id)
    )
    if section_id:
        query = query.filter(Student.section_id == section_id)
    return query.order_by(Student.id.asc()).all()


def get_section_for_school(db: Session, *, school_id: int, section_id: int) -> Section | None:
    return (
        db.query(Section)
        .filter(
            Section.id == section_id,
            Section.school_id == school_id,
        )
        .first()
    )


def list_sections_with_classes(
    db: Session,
    *,
    school_id: int,
) -> list[tuple[Section, Class]]:
    return (
        db.query(Section, Class)
        .join(Class, Class.id == Section.class_id)
        .filter(Section.school_id == school_id, Class.school_id == school_id)
        .all()
    )


def find_student_duplicate_by_roll_number(
    db: Session,
    *,
    school_id: int,
    section_id: int,
    roll_number: str,
) -> tuple[int] | None:
    return (
        db.query(Student.id)
        .filter(
            Student.school_id == school_id,
            Student.section_id == section_id,
            func.lower(Student.roll_number) == roll_number.lower(),
        )
        .first()
    )


def find_student_duplicate_by_identity(
    db: Session,
    *,
    school_id: int,
    section_id: int,
    full_name_key: str,
    parent_phone: str,
    date_of_birth: date | None,
) -> tuple[int] | None:
    query = db.query(Student.id).filter(
        Student.school_id == school_id,
        Student.section_id == section_id,
        func.lower(Student.name) == full_name_key,
        Student.parent_phone == parent_phone,
    )
    if date_of_birth is None:
        query = query.filter(Student.date_of_birth.is_(None))
    else:
        query = query.filter(Student.date_of_birth == date_of_birth)
    return query.first()


def create_import_batch(
    db: Session,
    *,
    token: str,
    school_id: int,
    user_id: int,
    payload: dict,
    expires_at: datetime,
) -> StudentImportBatch:
    batch = StudentImportBatch(
        id=token,
        school_id=school_id,
        user_id=user_id,
        payload=payload,
        expires_at=expires_at,
    )
    db.add(batch)
    db.commit()
    return batch


def get_import_batch(
    db: Session,
    *,
    import_token: str,
    school_id: int,
    user_id: int,
) -> StudentImportBatch | None:
    return (
        db.query(StudentImportBatch)
        .filter(
            StudentImportBatch.id == import_token,
            StudentImportBatch.school_id == school_id,
            StudentImportBatch.user_id == user_id,
        )
        .first()
    )


def resolve_student_by_ref(
    db: Session,
    *,
    school_id: int,
    student_ref: str,
) -> Student | None:
    if student_ref.isdigit():
        return (
            db.query(Student)
            .filter(
                Student.id == int(student_ref),
                Student.school_id == school_id,
            )
            .first()
        )
    return (
        db.query(Student)
        .filter(
            Student.public_id == student_ref,
            Student.school_id == school_id,
        )
        .first()
    )


def get_section_and_class_for_student(
    db: Session,
    *,
    school_id: int,
    section_id: int | None,
) -> tuple[Section | None, Class | None]:
    section = None
    class_ = None
    if section_id is not None:
        section = (
            db.query(Section)
            .filter(
                Section.id == section_id,
                Section.school_id == school_id,
            )
            .first()
        )
        if section:
            class_ = (
                db.query(Class)
                .filter(
                    Class.id == section.class_id,
                    Class.school_id == school_id,
                )
                .first()
            )
    return section, class_


def count_attendance(
    db: Session,
    *,
    school_id: int,
    student_id: int,
    attendance_status: str,
) -> int:
    return (
        db.query(func.count(AttendanceRecord.id))
        .filter(
            AttendanceRecord.school_id == school_id,
            AttendanceRecord.student_id == student_id,
            AttendanceRecord.status == attendance_status,
        )
        .scalar()
        or 0
    )


def list_recent_results(
    db: Session,
    *,
    school_id: int,
    student_id: int,
    limit: int,
) -> list[tuple[str, int, int, str]]:
    return (
        db.query(
            MarksRecord.exam_type,
            MarksRecord.marks_obtained,
            MarksRecord.max_marks,
            Subject.name.label("subject_name"),
        )
        .join(
            Subject,
            (Subject.id == MarksRecord.subject_id) & (Subject.school_id == school_id),
        )
        .filter(
            MarksRecord.school_id == school_id,
            MarksRecord.student_id == student_id,
        )
        .order_by(MarksRecord.created_at.desc())
        .limit(limit)
        .all()
    )


def list_report_card_results(
    db: Session,
    *,
    school_id: int,
    student_id: int,
) -> list[tuple[str, int, int, str]]:
    return (
        db.query(
            MarksRecord.exam_type,
            MarksRecord.marks_obtained,
            MarksRecord.max_marks,
            Subject.name.label("subject_name"),
        )
        .join(
            Subject,
            (Subject.id == MarksRecord.subject_id) & (Subject.school_id == school_id),
        )
        .filter(
            MarksRecord.school_id == school_id,
            MarksRecord.student_id == student_id,
        )
        .order_by(Subject.name.asc(), MarksRecord.created_at.desc())
        .all()
    )
