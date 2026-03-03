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
    status: str
    # Add this to prevent 'extra_forbidden' error
    school_id: Optional[int] = None


class AttendanceOut(BaseModel):
    id: Optional[int] = None
    school_id: int
    student_id: int
    student_name: Optional[str] = None
    section_id: Optional[int] = None
    class_name: Optional[str] = None
    section_name: Optional[str] = None
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
    section_id: int | None = Query(None),
    db: Session = Depends(get_db),
    school_id: int = Depends(get_valid_school_id),
):
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
        section_meta = {}
        if section_ids:
            from app.db.models.section import Section
            from app.db.models.class_ import Class

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

    students_query = db.query(Student).filter(Student.school_id == school_id)
    if section_id is not None:
        students_query = students_query.filter(Student.section_id == section_id)

    students = students_query.all()

    section_ids = {student.section_id for student in students if student.section_id is not None}
    section_meta = {}
    if section_ids:
        from app.db.models.section import Section
        from app.db.models.class_ import Class

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

# Change the POST route to handle the "upsert" logic as well
# to prevent errors if the frontend double-posts.


@router.post("", response_model=AttendanceOut, status_code=201)
def create_attendance(
    payload: AttendanceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    school_id: int = Depends(get_valid_school_id),
):
    """
    Handles POST requests. If a record already exists for this 
    student/date, it updates it instead of failing.
    """
    # 1. Check if it already exists (Idempotency)
    row = db.query(AttendanceRecord).filter(
        AttendanceRecord.student_id == payload.student_id,
        AttendanceRecord.date == payload.date,
        AttendanceRecord.school_id == school_id
    ).first()

    if row:
        # Update existing record (Fixes 409/Integrity errors)
        row.status = payload.status.lower()
        row.marked_by_user_id = current_user.id
    else:
        # Create new record
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
        raise HTTPException(
            status_code=400, detail="attendance_creation_failed")


@router.put("/{attendance_id}", response_model=AttendanceOut)
def update_attendance(
    attendance_id: int,
    payload: AttendanceUpdate,
    db: Session = Depends(get_db),
    school_id: int = Depends(get_valid_school_id),
    current_user: User = Depends(get_current_user),
    # These capture the extra info your frontend is already sending
    student_id: Optional[int] = Query(None),
    date: Optional[date_type] = Query(None),
):
    """
    TECH LEAD FIX: If attendance_id is 0, we perform an UPSERT based on 
    student_id and date.
    """
    row = None

    # 1. Try to find existing record
    if attendance_id > 0:
        row = db.query(AttendanceRecord).filter(
            AttendanceRecord.id == attendance_id,
            AttendanceRecord.school_id == school_id
        ).first()

    # Fallback to student/date lookup if ID is 0 or not found
    if not row and student_id and date:
        row = db.query(AttendanceRecord).filter(
            AttendanceRecord.student_id == student_id,
            AttendanceRecord.date == date,
            AttendanceRecord.school_id == school_id
        ).first()

    # 2. If no record exists, CREATE IT
    if not row:
        if not (student_id and date):
            raise HTTPException(
                status_code=400, detail="missing_info_for_new_record")

        row = AttendanceRecord(
            school_id=school_id,
            student_id=student_id,
            date=date,
            status=payload.status.lower(),  # Normalize to lowercase if needed
            marked_by_user_id=current_user.id
        )
        db.add(row)
    else:
        # 3. Update existing
        row.status = payload.status.lower()
        row.marked_by_user_id = current_user.id

    try:
        db.commit()
        db.refresh(row)
        return row
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/submit", response_model=AttendanceSubmissionOut, status_code=201)
def submit_attendance(
    payload: AttendanceSubmitIn,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    school_id: int = Depends(get_valid_school_id),
):
    existing = db.query(AttendanceSubmission).filter(
        AttendanceSubmission.school_id == school_id,
        AttendanceSubmission.section_id == payload.section_id,
        AttendanceSubmission.date == payload.date
    ).first()

    if existing:
        response.status_code = status.HTTP_200_OK
        return existing

    new_sub = AttendanceSubmission(
        school_id=school_id,
        section_id=payload.section_id,
        date=payload.date,
        submitted_by_user_id=current_user.id
    )
    db.add(new_sub)

    try:
        db.flush()
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
                    "type": "attendance", "student": s.name, "date": str(payload.date)
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
