from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, Response
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.v1.schemas.marks import (
    MarksRecordIn,
    MarksRecordOut,
    MarksSubmissionIn,
)
from app.db.models.marks_record import MarksRecord
from app.db.models.marks_submission import MarksSubmission
from app.db.models.user import User
from app.db.repositories import marks as marks_repository

MARKS_CORRECTION_WINDOW_DAYS = 7


def _normalize_exam_type(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9]+", "_", (value or "").strip().upper())
    normalized = normalized.strip("_")
    if not normalized:
        raise HTTPException(status_code=422, detail="invalid_exam_type")
    return normalized[:32]


def _is_submission_locked(submission: MarksSubmission) -> bool:
    cutoff = submission.created_at + timedelta(days=MARKS_CORRECTION_WINDOW_DAYS)
    now = datetime.now(timezone.utc)
    if cutoff.tzinfo is None:
        return now.replace(tzinfo=None) > cutoff.replace(tzinfo=None)
    return now > cutoff


def _enqueue_marks_outbox(
    *,
    db: Session,
    school_id: int,
    section_id: int,
    exam_type: str,
    marks_submission_id: int,
) -> None:
    students = marks_repository.list_section_students(
        db,
        school_id=school_id,
        section_id=section_id,
    )
    for student in students:
        marks_repository.add_notification_outbox(
            db,
            school_id=school_id,
            marks_submission_id=marks_submission_id,
            recipient_phone=student.parent_phone,
            payload=json.dumps(
                {
                    "type": "marks_submitted",
                    "student": student.name,
                    "exam": exam_type,
                }
            ),
        )


def record_marks(
    *,
    payload: MarksRecordIn,
    school_id: int,
    response: Response,
    db: Session,
    current_user: User,
) -> MarksRecord:
    if payload.max_marks <= 0:
        raise HTTPException(status_code=422, detail="invalid_max_marks")
    if payload.marks_obtained < 0 or payload.marks_obtained > payload.max_marks:
        raise HTTPException(status_code=422, detail="invalid_marks_range")

    student = marks_repository.get_student(
        db,
        school_id=school_id,
        student_id=payload.student_id,
    )
    if not student:
        raise HTTPException(status_code=400, detail="invalid_student_id")

    subject = marks_repository.get_subject(
        db,
        school_id=school_id,
        subject_id=payload.subject_id,
    )
    if not subject:
        raise HTTPException(status_code=400, detail="invalid_subject_id")

    exam_type = _normalize_exam_type(payload.exam_type)
    existing = marks_repository.get_marks_record(
        db,
        school_id=school_id,
        student_id=payload.student_id,
        subject_id=payload.subject_id,
        exam_type=exam_type,
    )
    if existing:
        if existing.marks_obtained == payload.marks_obtained and existing.max_marks == payload.max_marks:
            response.status_code = 200
            return existing

        submission = marks_repository.get_marks_submission(
            db,
            school_id=school_id,
            section_id=student.section_id,
            subject_id=payload.subject_id,
            exam_type=exam_type,
        )
        if submission and _is_submission_locked(submission):
            raise HTTPException(status_code=409, detail="marks_locked_after_7_days")

        existing.marks_obtained = payload.marks_obtained
        existing.max_marks = payload.max_marks
        existing.recorded_by_user_id = current_user.id
        db.commit()
        db.refresh(existing)
        response.status_code = 200
        return existing

    row = MarksRecord(
        school_id=school_id,
        student_id=payload.student_id,
        subject_id=payload.subject_id,
        exam_type=exam_type,
        marks_obtained=payload.marks_obtained,
        max_marks=payload.max_marks,
        recorded_by_user_id=current_user.id,
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="conflicting_marks")
    db.refresh(row)
    return row


def submit_marks(
    *,
    payload: MarksSubmissionIn,
    school_id: int,
    response: Response,
    db: Session,
    current_user: User,
) -> MarksSubmission:
    exam_type = _normalize_exam_type(payload.exam_type)
    existing = marks_repository.get_marks_submission(
        db,
        school_id=school_id,
        section_id=payload.section_id,
        subject_id=payload.subject_id,
        exam_type=exam_type,
    )
    if existing:
        response.status_code = 200
        return existing

    row = MarksSubmission(
        school_id=school_id,
        section_id=payload.section_id,
        subject_id=payload.subject_id,
        exam_type=exam_type,
        submitted_by_user_id=current_user.id,
        status="submitted",
    )
    db.add(row)
    try:
        db.flush()
        _enqueue_marks_outbox(
            db=db,
            school_id=school_id,
            section_id=payload.section_id,
            exam_type=exam_type,
            marks_submission_id=row.id,
        )
        db.commit()
        db.refresh(row)
        return row
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="submission_failed")


def list_marks(
    *,
    school_id: int,
    section_id: int | None,
    subject_id: int,
    exam_type: str,
    db: Session,
) -> list[MarksRecordOut]:
    normalized_exam_type = _normalize_exam_type(exam_type)
    if section_id is not None:
        if not marks_repository.section_exists(db, school_id=school_id, section_id=section_id):
            raise HTTPException(status_code=400, detail="invalid_section_id")

    rows = marks_repository.list_marks_records(
        db,
        school_id=school_id,
        subject_id=subject_id,
        exam_type=normalized_exam_type,
        section_id=section_id,
    )
    return [
        MarksRecordOut(
            id=record.id,
            school_id=record.school_id,
            student_id=record.student_id,
            subject_id=record.subject_id,
            exam_type=record.exam_type,
            marks_obtained=record.marks_obtained,
            max_marks=record.max_marks,
            recorded_by_user_id=record.recorded_by_user_id,
            student_name=student_name,
            roll_no=str(roll_no) if roll_no is not None else None,
            class_name=class_name,
            section_name=section_name,
            subject_name=subject_name,
            created_at=record.created_at,
        )
        for record, student_name, roll_no, class_name, section_name, subject_name in rows
    ]
