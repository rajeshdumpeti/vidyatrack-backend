import json
import re
from typing import List
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.v1.deps import get_db, get_current_user
from app.db.models.marks_record import MarksRecord
from app.db.models.marks_submission import MarksSubmission
from app.db.models.notification_outbox import NotificationOutbox
from app.db.models.class_ import Class
from app.db.models.section import Section
from app.db.models.student import Student
from app.db.models.subject import Subject
from app.db.models.user import User

router = APIRouter(prefix="/marks", tags=["marks"])
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
        return datetime.utcnow() > cutoff.replace(tzinfo=None)
    return now > cutoff

# --- SCHEMAS ---


class MarksRecordIn(BaseModel):
    student_id: int
    subject_id: int
    exam_type: str
    marks_obtained: int
    max_marks: int
    model_config = ConfigDict(extra="forbid")


class MarksSubmissionIn(BaseModel):
    section_id: int
    subject_id: int
    exam_type: str
    model_config = ConfigDict(extra="forbid")


class MarksRecordOut(BaseModel):
    id: int
    school_id: int
    student_id: int
    subject_id: int
    exam_type: str
    marks_obtained: int
    max_marks: int
    recorded_by_user_id: int | None
    student_name: str | None = None
    roll_no: str | None = None
    class_name: str | None = None
    section_name: str | None = None
    subject_name: str | None = None
    created_at: datetime  # FIX: Added for serialization
    model_config = ConfigDict(from_attributes=True)


class MarksSubmissionOut(BaseModel):
    id: int
    school_id: int
    section_id: int
    subject_id: int
    exam_type: str
    submitted_by_user_id: int | None
    status: str
    created_at: datetime  # FIX: Added for serialization
    model_config = ConfigDict(from_attributes=True)

# --- INTERNAL HELPERS ---


def _enqueue_marks_outbox(
    *,
    db: Session,
    school_id: int,
    section_id: int,
    subject_id: int,
    exam_type: str,
    marks_submission_id: int,
) -> None:
    students = (
        db.query(Student)
        .filter(Student.school_id == school_id, Student.section_id == section_id)
        .all()
    )

    for s in students:
        db.add(
            NotificationOutbox(
                school_id=school_id,
                event_type="MARKS_SUBMITTED",
                attendance_submission_id=None,  # Explicitly null for DB constraint
                marks_submission_id=marks_submission_id,
                recipient_phone=s.parent_phone,
                payload=json.dumps({
                    "type": "marks_submitted",
                    "student": s.name,
                    "exam": exam_type
                }),
                status="PENDING"
            )
        )

# --- ROUTES ---


@router.post("/record", response_model=MarksRecordOut, status_code=201)
def record_marks(
    payload: MarksRecordIn,
    school_id: int,  # FIX: Get from query param
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),  # FIX: Use User object
):
    # Validate student and subject in school
    if payload.max_marks <= 0:
        raise HTTPException(status_code=422, detail="invalid_max_marks")
    if payload.marks_obtained < 0 or payload.marks_obtained > payload.max_marks:
        raise HTTPException(status_code=422, detail="invalid_marks_range")

    student = db.query(Student).filter(
        Student.id == payload.student_id,
        Student.school_id == school_id
    ).first()
    if not student:
        raise HTTPException(status_code=400, detail="invalid_student_id")

    subject = db.query(Subject).filter(
        Subject.id == payload.subject_id,
        Subject.school_id == school_id
    ).first()
    if not subject:
        raise HTTPException(status_code=400, detail="invalid_subject_id")

    exam_type = _normalize_exam_type(payload.exam_type)

    existing = db.query(MarksRecord).filter(
        MarksRecord.school_id == school_id,
        MarksRecord.student_id == payload.student_id,
        MarksRecord.subject_id == payload.subject_id,
        MarksRecord.exam_type == exam_type,
    ).first()

    if existing:
        if (
            existing.marks_obtained == payload.marks_obtained
            and existing.max_marks == payload.max_marks
        ):
            response.status_code = 200
            return existing

        submission = db.query(MarksSubmission).filter(
            MarksSubmission.school_id == school_id,
            MarksSubmission.section_id == student.section_id,
            MarksSubmission.subject_id == payload.subject_id,
            MarksSubmission.exam_type == exam_type,
        ).first()
        if submission and _is_submission_locked(submission):
            raise HTTPException(
                status_code=409,
                detail="marks_locked_after_7_days",
            )

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
        recorded_by_user_id=current_user.id,  # FIX: use .id
    )
    db.add(row)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="conflicting_marks")

    db.refresh(row)
    return row


@router.post("/submit", response_model=MarksSubmissionOut, status_code=201)
def submit_marks(
    payload: MarksSubmissionIn,
    school_id: int,  # FIX: Get from query param
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    exam_type = _normalize_exam_type(payload.exam_type)

    # Check if exists
    existing = db.query(MarksSubmission).filter(
        MarksSubmission.school_id == school_id,
        MarksSubmission.section_id == payload.section_id,
        MarksSubmission.subject_id == payload.subject_id,
        MarksSubmission.exam_type == exam_type
    ).first()

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
            subject_id=payload.subject_id,
            exam_type=exam_type,
            marks_submission_id=row.id
        )
        db.commit()
        db.refresh(row)
        return row
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="submission_failed")


@router.get("", response_model=List[MarksRecordOut])
def list_marks(
    school_id: int,  # FIX: Consistent with Attendance
    section_id: int | None = Query(None),
    subject_id: int = Query(...),
    exam_type: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    normalized_exam_type = _normalize_exam_type(exam_type)

    if section_id is not None:
        section_exists = (
            db.query(Section.id)
            .filter(Section.school_id == school_id, Section.id == section_id)
            .first()
        )
        if not section_exists:
            raise HTTPException(status_code=400, detail="invalid_section_id")

    q = (
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
            (Subject.id == MarksRecord.subject_id)
            & (Subject.school_id == school_id),
        )
        .filter(
            MarksRecord.school_id == school_id,
            Student.school_id == school_id,
            MarksRecord.subject_id == subject_id,
            MarksRecord.exam_type == normalized_exam_type,
        )
        .order_by(MarksRecord.id.asc())
    )

    if section_id is not None:
        q = q.filter(Student.section_id == section_id)

    rows = q.all()
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
