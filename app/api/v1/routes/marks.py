from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.v1.deps import get_db, get_current_user
from app.db.models.marks_record import MarksRecord
from app.db.models.marks_submission import MarksSubmission
from app.db.models.section import Section
from app.db.models.student import Student
from app.db.models.subject import Subject

router = APIRouter(prefix="/marks", tags=["marks"])


class MarksRecordIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    student_id: int
    subject_id: int
    exam_type: str
    marks_obtained: int
    max_marks: int


class MarksSubmissionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    section_id: int
    subject_id: int
    exam_type: str


class MarksRecordOut(BaseModel):
    id: int
    school_id: int
    student_id: int
    subject_id: int
    exam_type: str
    marks_obtained: int
    max_marks: int
    recorded_by_user_id: int | None

    class Config:
        from_attributes = True


class MarksSubmissionOut(BaseModel):
    id: int
    school_id: int
    section_id: int
    subject_id: int
    exam_type: str
    submitted_by_user_id: int | None
    status: str

    class Config:
        from_attributes = True


@router.post("/record", response_model=MarksRecordOut, status_code=201)
def record_marks(
    payload: MarksRecordIn,
    response: Response,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    # Validate references belong to same school
    student = (
        db.query(Student)
        .filter(
            Student.id == payload.student_id,
            Student.school_id == current_user["school_id"],
        )
        .first()
    )
    if not student:
        raise HTTPException(status_code=400, detail="invalid_student_id")

    subject = (
        db.query(Subject)
        .filter(
            Subject.id == payload.subject_id,
            Subject.school_id == current_user["school_id"],
        )
        .first()
    )
    if not subject:
        raise HTTPException(status_code=400, detail="invalid_subject_id")

    row = MarksRecord(
        school_id=current_user["school_id"],
        student_id=payload.student_id,
        subject_id=payload.subject_id,
        exam_type=payload.exam_type,
        marks_obtained=payload.marks_obtained,
        max_marks=payload.max_marks,
        recorded_by_user_id=current_user["user_id"],
    )
    db.add(row)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()

        existing = (
            db.query(MarksRecord)
            .filter(
                MarksRecord.school_id == current_user["school_id"],
                MarksRecord.student_id == payload.student_id,
                MarksRecord.subject_id == payload.subject_id,
                MarksRecord.exam_type == payload.exam_type,
            )
            .first()
        )
        if (
            existing
            and existing.marks_obtained == payload.marks_obtained
            and existing.max_marks == payload.max_marks
        ):
            response.status_code = status.HTTP_200_OK
            return existing

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="conflicting_marks",
        )

    db.refresh(row)
    return row


@router.post("/submit", response_model=MarksSubmissionOut, status_code=201)
def submit_marks(
    payload: MarksSubmissionIn,
    response: Response,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    # Validate section + subject belong to same school
    sec = (
        db.query(Section)
        .filter(
            Section.id == payload.section_id,
            Section.school_id == current_user["school_id"],
        )
        .first()
    )
    if not sec:
        raise HTTPException(status_code=400, detail="invalid_section_id")

    subject = (
        db.query(Subject)
        .filter(
            Subject.id == payload.subject_id,
            Subject.school_id == current_user["school_id"],
        )
        .first()
    )
    if not subject:
        raise HTTPException(status_code=400, detail="invalid_subject_id")

    row = MarksSubmission(
        school_id=current_user["school_id"],
        section_id=payload.section_id,
        subject_id=payload.subject_id,
        exam_type=payload.exam_type,
        submitted_by_user_id=current_user["user_id"],
        status="submitted",
    )
    db.add(row)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()

        existing = (
            db.query(MarksSubmission)
            .filter(
                MarksSubmission.school_id == current_user["school_id"],
                MarksSubmission.section_id == payload.section_id,
                MarksSubmission.subject_id == payload.subject_id,
                MarksSubmission.exam_type == payload.exam_type,
            )
            .first()
        )
        if existing:
            response.status_code = status.HTTP_200_OK
            return existing

        raise HTTPException(status_code=409, detail="already_submitted")

    db.refresh(row)
    return row


@router.get("", response_model=List[MarksRecordOut])
def list_marks(
    section_id: int = Query(...),
    subject_id: int = Query(...),
    exam_type: str = Query(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    # Validate section + subject belong to same school (tenant isolation)
    sec = (
        db.query(Section)
        .filter(
            Section.id == section_id,
            Section.school_id == current_user["school_id"],
        )
        .first()
    )
    if not sec:
        raise HTTPException(status_code=400, detail="invalid_section_id")

    subject = (
        db.query(Subject)
        .filter(
            Subject.id == subject_id,
            Subject.school_id == current_user["school_id"],
        )
        .first()
    )
    if not subject:
        raise HTTPException(status_code=400, detail="invalid_subject_id")

    # NOTE: Without student↔section enrollment mapping, we can only return
    # marks scoped by school+subject+exam_type. Section validation prevents cross-tenant access.
    return (
        db.query(MarksRecord)
        .filter(
            MarksRecord.school_id == current_user["school_id"],
            MarksRecord.subject_id == subject_id,
            MarksRecord.exam_type == exam_type,
        )
        .order_by(MarksRecord.id.asc())
        .all()
    )
