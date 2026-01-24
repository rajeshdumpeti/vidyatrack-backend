import json

from datetime import date as date_type, datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.v1.deps import get_db, get_current_user
from app.db.models.attendance_record import AttendanceRecord
from app.db.models.student import Student
from app.db.models.attendance_submission import AttendanceSubmission
from app.db.models.section import Section
from app.db.models.notification_outbox import NotificationOutbox
from app.db.models.teacher import Teacher
from app.db.models.teacher_primary_section import TeacherPrimarySection

router = APIRouter(prefix="/attendance", tags=["attendance"])


class AttendanceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    student_id: int
    date: date_type
    status: str  # "present" | "absent"


class AttendanceOut(BaseModel):
    id: int
    school_id: int
    student_id: int
    date: date_type
    status: str
    marked_by_user_id: int | None

    class Config:
        from_attributes = True


class AttendanceSubmitIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    section_id: int
    date: date_type


class AttendanceSubmissionOut(BaseModel):
    id: int
    school_id: int
    section_id: int
    date: date_type
    submitted_by_user_id: int | None

    class Config:
        from_attributes = True


class AttendanceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: str  # "PRESENT" | "ABSENT"


@router.post("", response_model=AttendanceOut, status_code=201)
def create_attendance(
    payload: AttendanceCreate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    # Validate student belongs to same school (tenant isolation)
    student = (
        db.query(Student)
        .filter(
            Student.id == payload.student_id,
            Student.school_id == current_user["school_id"],
        )
        .first()
    )
    if not student:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invalid_student_id",
        )

    row = AttendanceRecord(
        school_id=current_user["school_id"],
        student_id=payload.student_id,
        date=payload.date,
        status=payload.status,
        marked_by_user_id=current_user["user_id"],
    )

    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()

        existing = (
            db.query(AttendanceRecord)
            .filter(
                AttendanceRecord.school_id == current_user["school_id"],
                AttendanceRecord.student_id == payload.student_id,
                AttendanceRecord.date == payload.date,
            )
            .first()
        )
        if existing and existing.status == payload.status:
            # True idempotency: same status => return existing record as 200
            response.status_code = status.HTTP_200_OK
            return existing

        # Conflict: same student+date already exists but status differs
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="conflicting_status",
        )

    db.refresh(row)
    return row


@router.get("", response_model=list[AttendanceOut])
def list_attendance(
    date: date_type = Query(..., description="Attendance date in YYYY-MM-DD"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return (
        db.query(AttendanceRecord)
        .filter(
            AttendanceRecord.school_id == current_user["school_id"],
            AttendanceRecord.date == date,
        )
        .order_by(AttendanceRecord.id.asc())
        .all()
    )


@router.post("/submit", response_model=AttendanceSubmissionOut, status_code=201)
def submit_attendance(
    payload: AttendanceSubmitIn,
    response: Response,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    # Validate section belongs to same school (tenant isolation)
    sec = (
        db.query(Section)
        .filter(
            Section.id == payload.section_id,
            Section.school_id == current_user["school_id"],
        )
        .first()
    )
    if not sec:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invalid_section_id",
        )

    row = AttendanceSubmission(
        school_id=current_user["school_id"],
        section_id=payload.section_id,
        date=payload.date,
        submitted_by_user_id=current_user["user_id"],
    )

    db.add(row)

    try:
        # flush so row.id is available before enqueue
        db.flush()

        # recipients = all students in the submitted section for this school
        students = (
            db.query(Student)
            .filter(
                Student.school_id == current_user["school_id"],
                Student.section_id == payload.section_id,
            )
            .all()
        )

        # enqueue outbox rows (deduped by unique constraint)
        for s in students:
            db.add(
                NotificationOutbox(
                    school_id=current_user["school_id"],
                    event_type="ATTENDANCE_SUBMITTED",
                    attendance_submission_id=row.id,
                    marks_submission_id=None,
                    recipient_phone=s.parent_phone,
                    payload=json.dumps(
                        {
                            "type": "attendance_submitted",
                            "date": str(payload.date),
                            "student_id": s.id,
                            "section_id": payload.section_id,
                        }
                    ),
                    status="PENDING",
                    attempts=0,
                )
            )

        db.commit()

    except IntegrityError:
        db.rollback()

        existing = (
            db.query(AttendanceSubmission)
            .filter(
                AttendanceSubmission.school_id == current_user["school_id"],
                AttendanceSubmission.section_id == payload.section_id,
                AttendanceSubmission.date == payload.date,
            )
            .first()
        )
        if existing:
            # Idempotent submit: do NOT enqueue again
            response.status_code = status.HTTP_200_OK
            return existing

        raise HTTPException(status_code=409, detail="already_submitted")

    db.refresh(row)
    return row


@router.put("/{attendance_id}", response_model=AttendanceOut)
def update_attendance(
    attendance_id: int,
    payload: AttendanceUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    # TEACHER-only
    if current_user.get("role") != "TEACHER":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="insufficient_permissions",
        )

    school_id = current_user["school_id"]
    user_id = current_user["user_id"]

    # Fetch attendance record tenant-scoped (no leakage)
    row = (
        db.query(AttendanceRecord)
        .filter(
            AttendanceRecord.id == attendance_id,
            AttendanceRecord.school_id == school_id,
        )
        .first()
    )
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="attendance_not_found")

    # Same-day edit (India calendar date)
    today_ist = datetime.now(ZoneInfo("Asia/Kolkata")).date()
    if row.date != today_ist:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="attendance_edit_not_allowed",
        )

    # Resolve teacher via teachers.user_id + tenant scope
    teacher = (
        db.query(Teacher)
        .filter(
            Teacher.school_id == school_id,
            Teacher.user_id == user_id,
        )
        .first()
    )
    if not teacher:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="teacher_not_found")

    # Resolve teacher primary section
    mapping = (
        db.query(TeacherPrimarySection)
        .filter(
            TeacherPrimarySection.school_id == school_id,
            TeacherPrimarySection.teacher_id == teacher.id,
        )
        .first()
    )
    if not mapping:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="no_primary_section_assigned")

    # Student must be in teacher's primary section
    student = (
        db.query(Student)
        .filter(
            Student.id == row.student_id,
            Student.school_id == school_id,
        )
        .first()
    )
    if not student:
        # should not happen if FK integrity is good; still avoid leaking
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="attendance_not_found")

    if getattr(student, "section_id", None) != mapping.section_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="out_of_scope",
        )

    # Validate + normalize status (request is PRESENT/ABSENT)
    s = payload.status.strip().upper()
    if s not in ("PRESENT", "ABSENT"):
        # keep it simple; 422 could be better but this is deterministic and explicit
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_status")

    # Update only status; do not change student_id/date/school_id
    # For consistency with existing data ("present"/"absent"), normalize to lowercase
    row.status = "present" if s == "PRESENT" else "absent"

    # Audit-safe: mark who edited (recommended)
    row.marked_by_user_id = user_id

    db.commit()
    db.refresh(row)
    return row
