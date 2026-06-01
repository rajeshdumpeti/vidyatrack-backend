from typing import List

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.api.v1.controllers import marks as marks_controller
from app.api.v1.deps import get_db, get_current_user, require_school_module
from app.api.v1.schemas.marks import (
    MarksRecordIn,
    MarksRecordOut,
    MarksSubmissionIn,
    MarksSubmissionOut,
)
from app.db.models.marks_record import MarksRecord
from app.db.models.marks_submission import MarksSubmission
from app.db.models.user import User

router = APIRouter(prefix="/marks", tags=["marks"])
MARKS_CORRECTION_WINDOW_DAYS = 7


@router.post("/record", response_model=MarksRecordOut, status_code=201)
def record_marks(
    payload: MarksRecordIn,
    response: Response,
    school_id: int = Depends(require_school_module("exams")),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),  # FIX: Use User object
) -> MarksRecord:
    return marks_controller.record_marks(
        payload=payload,
        school_id=school_id,
        response=response,
        db=db,
        current_user=current_user,
    )


@router.post("/submit", response_model=MarksSubmissionOut, status_code=201)
def submit_marks(
    payload: MarksSubmissionIn,
    response: Response,
    school_id: int = Depends(require_school_module("exams")),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MarksSubmission:
    return marks_controller.submit_marks(
        payload=payload,
        school_id=school_id,
        response=response,
        db=db,
        current_user=current_user,
    )


@router.get("", response_model=List[MarksRecordOut])
def list_marks(
    school_id: int = Depends(require_school_module("exams")),
    section_id: int | None = Query(None),
    subject_id: int = Query(...),
    exam_type: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[MarksRecordOut]:
    return marks_controller.list_marks(
        school_id=school_id,
        section_id=section_id,
        subject_id=subject_id,
        exam_type=exam_type,
        db=db,
    )
