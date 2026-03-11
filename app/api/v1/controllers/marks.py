from fastapi import Response
from sqlalchemy.orm import Session

from app.api.v1.schemas.marks import (
    MarksRecordIn,
    MarksRecordOut,
    MarksSubmissionIn,
    MarksSubmissionOut,
)
from app.db.models.marks_record import MarksRecord
from app.db.models.marks_submission import MarksSubmission
from app.db.models.user import User
from app.services import marks as marks_service


def record_marks(
    *,
    payload: MarksRecordIn,
    school_id: int,
    response: Response,
    db: Session,
    current_user: User,
) -> MarksRecord:
    return marks_service.record_marks(
        payload=payload,
        school_id=school_id,
        response=response,
        db=db,
        current_user=current_user,
    )


def submit_marks(
    *,
    payload: MarksSubmissionIn,
    school_id: int,
    response: Response,
    db: Session,
    current_user: User,
) -> MarksSubmission:
    return marks_service.submit_marks(
        payload=payload,
        school_id=school_id,
        response=response,
        db=db,
        current_user=current_user,
    )


def list_marks(
    *,
    school_id: int,
    section_id: int | None,
    subject_id: int,
    exam_type: str,
    db: Session,
) -> list[MarksRecordOut]:
    return marks_service.list_marks(
        school_id=school_id,
        section_id=section_id,
        subject_id=subject_id,
        exam_type=exam_type,
        db=db,
    )
