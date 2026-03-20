from __future__ import annotations

import json
from datetime import date as date_type

from fastapi import HTTPException, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.v1.schemas.attendance import (
    AttendanceCreate,
    AttendanceOut,
    AttendanceSubmitIn,
    AttendanceUpdate,
)
from app.db.models.attendance_record import AttendanceRecord
from app.db.models.attendance_submission import AttendanceSubmission
from app.db.models.notification_outbox import NotificationOutbox
from app.db.models.student import Student
from app.db.models.user import User


def list_attendance(
    *,
    db: Session,
    school_id: int,
    date: date_type,
    section_id: int | None,
    include_defaults: bool,
) -> list[AttendanceOut]:
    if date > date_type.today():
        raise HTTPException(status_code=400, detail="future_date_not_allowed")

    records_query = (
        db.query(
            AttendanceRecord,
            Student.name.label("student_name"),
            Student.section_id.label("section_id"),
        )
        .join(Student, Student.id == AttendanceRecord.student_id)
        .filter(
            AttendanceRecord.school_id == school_id,
            AttendanceRecord.date == date,
        )
    )
    if section_id is not None:
        records_query = records_query.filter(Student.section_id == section_id)

    records = records_query.all()
    if records:
        section_ids = {
            student_section_id
            for _, _, student_section_id in records
            if student_section_id is not None
        }
        section_meta: dict[int, dict[str, str]] = {}
        if section_ids:
            from app.db.models.class_ import Class
            from app.db.models.section import Section

            section_rows = (
                db.query(
                    Section.id.label("section_id"),
                    Section.name.label("section_name"),
                    Class.name.label("class_name"),
                )
                .join(Class, Class.id == Section.class_id)
                .filter(
                    Section.school_id == school_id,
                    Section.id.in_(section_ids),
                )
                .all()
            )
            section_meta = {
                row.section_id: {
                    "class_name": row.class_name,
                    "section_name": row.section_name,
                }
                for row in section_rows
            }

        return [
            AttendanceOut(
                id=record.id,
                school_id=record.school_id,
                student_id=record.student_id,
                student_name=student_name,
                section_id=student_section_id,
                class_name=section_meta.get(student_section_id, {}).get("class_name"),
                section_name=section_meta.get(student_section_id, {}).get("section_name"),
                date=record.date,
                status=record.status,
                marked_by_user_id=record.marked_by_user_id,
            )
            for record, student_name, student_section_id in records
        ]

    if not include_defaults:
        return []

    students_query = db.query(Student).filter(Student.school_id == school_id)
    if section_id is not None:
        students_query = students_query.filter(Student.section_id == section_id)
    students = students_query.all()

    section_ids = {student.section_id for student in students if student.section_id is not None}
    section_meta: dict[int, dict[str, str]] = {}
    if section_ids:
        from app.db.models.class_ import Class
        from app.db.models.section import Section

        section_rows = (
            db.query(
                Section.id.label("section_id"),
                Section.name.label("section_name"),
                Class.name.label("class_name"),
            )
            .join(Class, Class.id == Section.class_id)
            .filter(
                Section.school_id == school_id,
                Section.id.in_(section_ids),
            )
            .all()
        )
        section_meta = {
            row.section_id: {
                "class_name": row.class_name,
                "section_name": row.section_name,
            }
            for row in section_rows
        }

    return [
        AttendanceOut(
            id=0,
            school_id=school_id,
            student_id=student.id,
            student_name=student.name,
            section_id=student.section_id,
            class_name=section_meta.get(student.section_id, {}).get("class_name"),
            section_name=section_meta.get(student.section_id, {}).get("section_name"),
            date=date,
            status="present",
            marked_by_user_id=None,
        )
        for student in students
    ]


def create_attendance(
    *,
    payload: AttendanceCreate,
    db: Session,
    current_user: User,
    school_id: int,
) -> AttendanceRecord:
    row = (
        db.query(AttendanceRecord)
        .filter(
            AttendanceRecord.student_id == payload.student_id,
            AttendanceRecord.date == payload.date,
            AttendanceRecord.school_id == school_id,
        )
        .first()
    )

    if row:
        row.status = payload.status.lower()
        row.marked_by_user_id = current_user.id
    else:
        row = AttendanceRecord(
            school_id=school_id,
            student_id=payload.student_id,
            date=payload.date,
            status=payload.status.lower(),
            marked_by_user_id=current_user.id,
        )
        db.add(row)

    try:
        db.commit()
        db.refresh(row)
        return row
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="attendance_creation_failed")


def update_attendance(
    *,
    attendance_id: int,
    payload: AttendanceUpdate,
    db: Session,
    school_id: int,
    current_user: User,
    student_id: int | None,
    date: date_type | None,
) -> AttendanceRecord:
    row = None
    if attendance_id > 0:
        row = (
            db.query(AttendanceRecord)
            .filter(
                AttendanceRecord.id == attendance_id,
                AttendanceRecord.school_id == school_id,
            )
            .first()
        )

    if not row and student_id and date:
        row = (
            db.query(AttendanceRecord)
            .filter(
                AttendanceRecord.student_id == student_id,
                AttendanceRecord.date == date,
                AttendanceRecord.school_id == school_id,
            )
            .first()
        )

    if not row:
        if not (student_id and date):
            raise HTTPException(status_code=400, detail="missing_info_for_new_record")

        row = AttendanceRecord(
            school_id=school_id,
            student_id=student_id,
            date=date,
            status=payload.status.lower(),
            marked_by_user_id=current_user.id,
        )
        db.add(row)
    else:
        row.status = payload.status.lower()
        row.marked_by_user_id = current_user.id

    try:
        db.commit()
        db.refresh(row)
        return row
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(exc))


def submit_attendance(
    *,
    payload: AttendanceSubmitIn,
    response: Response,
    db: Session,
    current_user: User,
    school_id: int,
) -> AttendanceSubmission:
    existing = (
        db.query(AttendanceSubmission)
        .filter(
            AttendanceSubmission.school_id == school_id,
            AttendanceSubmission.section_id == payload.section_id,
            AttendanceSubmission.date == payload.date,
        )
        .first()
    )
    if existing:
        response.status_code = status.HTTP_200_OK
        return existing

    new_submission = AttendanceSubmission(
        school_id=school_id,
        section_id=payload.section_id,
        date=payload.date,
        submitted_by_user_id=current_user.id,
    )
    db.add(new_submission)

    try:
        db.flush()
        students = (
            db.query(Student)
            .filter(
                Student.school_id == school_id,
                Student.section_id == payload.section_id,
            )
            .all()
        )
        for student in students:
            db.add(
                NotificationOutbox(
                    school_id=school_id,
                    event_type="ATTENDANCE_SUBMITTED",
                    attendance_submission_id=new_submission.id,
                    marks_submission_id=None,
                    recipient_phone=student.parent_phone,
                    payload=json.dumps(
                        {
                            "type": "attendance",
                            "student": student.name,
                            "date": str(payload.date),
                        }
                    ),
                    status="PENDING",
                )
            )

        db.commit()
        db.refresh(new_submission)
        return new_submission
    except IntegrityError:
        db.rollback()
        final_check = (
            db.query(AttendanceSubmission)
            .filter(
                AttendanceSubmission.school_id == school_id,
                AttendanceSubmission.section_id == payload.section_id,
                AttendanceSubmission.date == payload.date,
            )
            .first()
        )
        if final_check:
            return final_check
        raise HTTPException(status_code=400, detail="submission_failed")
