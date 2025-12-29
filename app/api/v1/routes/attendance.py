from datetime import date as date_type

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.v1.deps import get_db, get_current_user
from app.db.models.attendance_record import AttendanceRecord
from app.db.models.student import Student

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


@router.post("", response_model=AttendanceOut, status_code=201)
def create_attendance(
    payload: AttendanceCreate,
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
        # Unique constraint conflict => already marked for this student+date within the school
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="already_marked",
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
