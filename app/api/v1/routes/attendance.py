from datetime import datetime, date as date_type
import json
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.v1.deps import get_db, get_current_user, get_valid_school_id
from app.db.models.attendance_record import AttendanceRecord
from app.db.models.student import Student
from app.db.models.attendance_submission import AttendanceSubmission
from app.db.models.notification_outbox import NotificationOutbox
from app.db.models.user import User

router = APIRouter(prefix="/attendance", tags=["attendance"])

# --- SCHEMAS ---


class AttendanceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    student_id: int
    date: date_type
    status: str  # "present" | "absent"


class AttendanceOut(BaseModel):
    id: Optional[int] = None
    school_id: int
    student_id: int
    student_name: Optional[str] = None
    date: date_type
    status: str
    marked_by_user_id: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)


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
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AttendanceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: str  # "PRESENT" | "ABSENT"
    student_id: Optional[int] = None
    date: Optional[date_type] = None

# --- ROUTES ---


@router.get("", response_model=List[AttendanceOut])
def list_attendance(
    date: date_type = Query(...),
    section_id: int = Query(...),
    db: Session = Depends(get_db),
    # Use dependency to force validation of ?school_id=X
    school_id: int = Depends(get_valid_school_id),
):
    """
    Fetches existing records or generates a template based on the student list.
    """
    # 1. Try to find existing attendance records for the section/date
    records = (
        db.query(AttendanceRecord)
        .join(Student, Student.id == AttendanceRecord.student_id)
        .filter(
            AttendanceRecord.school_id == school_id,
            AttendanceRecord.date == date,
            Student.section_id == section_id
        )
        .all()
    )

    if records:
        for r in records:
            student = db.query(Student).filter(
                Student.id == r.student_id).first()
            r.student_name = student.name if student else "Unknown"
        return records

    # 2. Fallback: Return a "present" template for all students in that section
    students = db.query(Student).filter(
        Student.section_id == section_id,
        Student.school_id == school_id
    ).all()

    return [
        AttendanceOut(
            id=0,
            school_id=school_id,
            student_id=s.id,
            student_name=s.name,
            date=date,
            status="present",
            marked_by_user_id=None
        ) for s in students
    ]


@router.post("", response_model=AttendanceOut, status_code=201)
def create_attendance(
    payload: AttendanceCreate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    school_id: int = Depends(get_valid_school_id),
):
    """
    Creates a single attendance record.
    """
    # Verify student exists within the specified school context
    student = db.query(Student).filter(
        Student.id == payload.student_id,
        Student.school_id == school_id,
    ).first()

    if not student:
        raise HTTPException(
            status_code=400, detail="invalid_student_id_for_school")

    row = AttendanceRecord(
        school_id=school_id,
        student_id=payload.student_id,
        date=payload.date,
        status=payload.status,
        marked_by_user_id=current_user.id,
    )
    db.add(row)
    try:
        db.commit()
        db.refresh(row)
        return row
    except IntegrityError:
        db.rollback()
        # Handle existing record for idempotency/conflict resolution
        existing = db.query(AttendanceRecord).filter(
            AttendanceRecord.school_id == school_id,
            AttendanceRecord.student_id == payload.student_id,
            AttendanceRecord.date == payload.date,
        ).first()

        if existing:
            if existing.status == payload.status:
                response.status_code = status.HTTP_200_OK
                return existing
            else:
                raise HTTPException(
                    status_code=409, detail="conflicting_status")
        raise HTTPException(status_code=400, detail="creation_failed")


@router.put("/{attendance_id}", response_model=AttendanceOut)
def update_attendance(
    attendance_id: int,
    payload: AttendanceUpdate,
    db: Session = Depends(get_db),
    school_id: int = Depends(get_valid_school_id),
):
    """
    Updates status for an existing attendance record.
    """
    row = db.query(AttendanceRecord).filter(
        AttendanceRecord.id == attendance_id,
        AttendanceRecord.school_id == school_id
    ).first()

    if not row:
        raise HTTPException(status_code=404, detail="attendance_not_found")

    row.status = payload.status
    db.commit()
    db.refresh(row)
    return row


@router.post("/submit", response_model=AttendanceSubmissionOut, status_code=201)
def submit_attendance(
    payload: AttendanceSubmitIn,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    school_id: int = Depends(get_valid_school_id),
):
    """
    Finalizes attendance for a section and queues parent notifications.
    """
    # 1. Check for existing submission
    existing = db.query(AttendanceSubmission).filter(
        AttendanceSubmission.school_id == school_id,
        AttendanceSubmission.section_id == payload.section_id,
        AttendanceSubmission.date == payload.date
    ).first()

    if existing:
        response.status_code = status.HTTP_200_OK
        return existing

    # 2. Create the Submission record
    new_sub = AttendanceSubmission(
        school_id=school_id,
        section_id=payload.section_id,
        date=payload.date,
        submitted_by_user_id=current_user.id
    )
    db.add(new_sub)

    try:
        db.flush()

        # 3. Queue notifications for the Outbox
        students = db.query(Student).filter(
            Student.school_id == school_id,
            Student.section_id == payload.section_id
        ).all()

        for s in students:
            db.add(NotificationOutbox(
                school_id=school_id,
                event_type="ATTENDANCE_SUBMITTED",
                attendance_submission_id=new_sub.id,
                marks_submission_id=None,
                recipient_phone=s.parent_phone,
                payload=json.dumps({
                    "type": "attendance",
                    "student": s.name,
                    "date": str(payload.date)
                }),
                status="PENDING"
            ))

        db.commit()
        db.refresh(new_sub)
        return new_sub

    except IntegrityError:
        db.rollback()
        final_check = db.query(AttendanceSubmission).filter(
            AttendanceSubmission.school_id == school_id,
            AttendanceSubmission.section_id == payload.section_id,
            AttendanceSubmission.date == payload.date
        ).first()
        if final_check:
            return final_check
        raise HTTPException(status_code=400, detail="submission_failed")
