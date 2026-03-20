from datetime import date as date_type
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.api.v1.controllers import attendance as attendance_controller
from app.api.v1.deps import get_db, get_current_user, get_valid_school_id
from app.api.v1.schemas.attendance import (
    AttendanceCreate,
    AttendanceOut,
    AttendanceSubmissionOut,
    AttendanceSubmitIn,
    AttendanceUpdate,
)
from app.db.models.attendance_record import AttendanceRecord
from app.db.models.attendance_submission import AttendanceSubmission
from app.db.models.user import User

router = APIRouter(prefix="/attendance", tags=["attendance"])


@router.get("", response_model=List[AttendanceOut])
def list_attendance(
    date: date_type = Query(...),
    section_id: int | None = Query(None),
    include_defaults: bool = Query(False),
    db: Session = Depends(get_db),
    school_id: int = Depends(get_valid_school_id),
) -> list[AttendanceOut]:
    return attendance_controller.list_attendance(
        db=db,
        school_id=school_id,
        date=date,
        section_id=section_id,
        include_defaults=include_defaults,
    )

# Change the POST route to handle the "upsert" logic as well
# to prevent errors if the frontend double-posts.


@router.post("", response_model=AttendanceOut, status_code=201)
def create_attendance(
    payload: AttendanceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    school_id: int = Depends(get_valid_school_id),
) -> AttendanceRecord:
    return attendance_controller.create_attendance(
        payload=payload,
        db=db,
        current_user=current_user,
        school_id=school_id,
    )


@router.put("/{attendance_id}", response_model=AttendanceOut)
def update_attendance(
    attendance_id: int,
    payload: AttendanceUpdate,
    db: Session = Depends(get_db),
    school_id: int = Depends(get_valid_school_id),
    current_user: User = Depends(get_current_user),
    student_id: Optional[int] = Query(None),
    date: Optional[date_type] = Query(None),
) -> AttendanceRecord:
    return attendance_controller.update_attendance(
        attendance_id=attendance_id,
        payload=payload,
        db=db,
        school_id=school_id,
        current_user=current_user,
        student_id=student_id,
        date=date,
    )


@router.post("/submit", response_model=AttendanceSubmissionOut, status_code=201)
def submit_attendance(
    payload: AttendanceSubmitIn,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    school_id: int = Depends(get_valid_school_id),
) -> AttendanceSubmission:
    return attendance_controller.submit_attendance(
        payload=payload,
        response=response,
        db=db,
        current_user=current_user,
        school_id=school_id,
    )
