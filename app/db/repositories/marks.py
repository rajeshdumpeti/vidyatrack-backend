from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models.class_ import Class
from app.db.models.marks_record import MarksRecord
from app.db.models.marks_submission import MarksSubmission
from app.db.models.notification_outbox import NotificationOutbox
from app.db.models.section import Section
from app.db.models.student import Student
from app.db.models.subject import Subject


def get_student(db: Session, *, school_id: int, student_id: int) -> Student | None:
    return (
        db.query(Student)
        .filter(Student.id == student_id, Student.school_id == school_id)
        .first()
    )


def get_subject(db: Session, *, school_id: int, subject_id: int) -> Subject | None:
    return (
        db.query(Subject)
        .filter(Subject.id == subject_id, Subject.school_id == school_id)
        .first()
    )


def get_marks_record(
    db: Session,
    *,
    school_id: int,
    student_id: int,
    subject_id: int,
    exam_type: str,
) -> MarksRecord | None:
    return (
        db.query(MarksRecord)
        .filter(
            MarksRecord.school_id == school_id,
            MarksRecord.student_id == student_id,
            MarksRecord.subject_id == subject_id,
            MarksRecord.exam_type == exam_type,
        )
        .first()
    )


def get_marks_submission(
    db: Session,
    *,
    school_id: int,
    section_id: int,
    subject_id: int,
    exam_type: str,
) -> MarksSubmission | None:
    return (
        db.query(MarksSubmission)
        .filter(
            MarksSubmission.school_id == school_id,
            MarksSubmission.section_id == section_id,
            MarksSubmission.subject_id == subject_id,
            MarksSubmission.exam_type == exam_type,
        )
        .first()
    )


def list_section_students(db: Session, *, school_id: int, section_id: int) -> list[Student]:
    return (
        db.query(Student)
        .filter(Student.school_id == school_id, Student.section_id == section_id)
        .all()
    )


def add_notification_outbox(
    db: Session,
    *,
    school_id: int,
    marks_submission_id: int,
    recipient_phone: str | None,
    payload: str,
) -> None:
    db.add(
        NotificationOutbox(
            school_id=school_id,
            event_type="MARKS_SUBMITTED",
            attendance_submission_id=None,
            marks_submission_id=marks_submission_id,
            recipient_phone=recipient_phone,
            payload=payload,
            status="PENDING",
        )
    )


def section_exists(db: Session, *, school_id: int, section_id: int) -> bool:
    return (
        db.query(Section.id)
        .filter(Section.school_id == school_id, Section.id == section_id)
        .first()
        is not None
    )


def list_marks_records(
    db: Session,
    *,
    school_id: int,
    subject_id: int,
    exam_type: str,
    section_id: int | None,
):
    query = (
        db.query(
            MarksRecord,
            Student.name.label("student_name"),
            Student.roll_number.label("roll_no"),
            Class.name.label("class_name"),
            Section.name.label("section_name"),
            Subject.name.label("subject_name"),
        )
        .join(Student, Student.id == MarksRecord.student_id)
        .join(Section, Section.id == Student.section_id, isouter=True)
        .join(Class, Class.id == Section.class_id, isouter=True)
        .join(
            Subject,
            (Subject.id == MarksRecord.subject_id) & (Subject.school_id == school_id),
        )
        .filter(
            MarksRecord.school_id == school_id,
            Student.school_id == school_id,
            MarksRecord.subject_id == subject_id,
            MarksRecord.exam_type == exam_type,
        )
        .order_by(MarksRecord.id.asc())
    )
    if section_id is not None:
        query = query.filter(Student.section_id == section_id)
    return query.all()

