from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user, get_db, require_management
from app.db.models.section import Section
from app.db.models.subject import Subject
from app.db.models.teacher import Teacher
from app.db.models.section_subject_teacher import SectionSubjectTeacher

router = APIRouter(prefix="/teaching-assignments",
                   tags=["teaching-assignments"])


class TeachingAssignmentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    section_id: int
    subject_id: int
    teacher_id: int


class TeachingAssignmentOut(BaseModel):
    id: int
    school_id: int
    section_id: int
    subject_id: int
    teacher_id: int

    class Config:
        from_attributes = True


@router.post("", response_model=TeachingAssignmentOut, status_code=201)
def create_teaching_assignment(
    payload: TeachingAssignmentCreate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_management),
):
    # Validate references belong to same tenant (school)
    sec = (
        db.query(Section)
        .filter(
            Section.id == payload.section_id,
            Section.school_id == current_user["school_id"],
        )
        .first()
    )
    if not sec:
        raise HTTPException(status_code=400, detail="invalid_reference")

    subj = (
        db.query(Subject)
        .filter(
            Subject.id == payload.subject_id,
            Subject.school_id == current_user["school_id"],
        )
        .first()
    )
    if not subj:
        raise HTTPException(status_code=400, detail="invalid_reference")

    t = (
        db.query(Teacher)
        .filter(
            Teacher.id == payload.teacher_id,
            Teacher.school_id == current_user["school_id"],
        )
        .first()
    )
    if not t:
        raise HTTPException(status_code=400, detail="invalid_reference")

    row = SectionSubjectTeacher(
        school_id=current_user["school_id"],
        section_id=payload.section_id,
        subject_id=payload.subject_id,
        teacher_id=payload.teacher_id,
    )
    db.add(row)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()

        existing = (
            db.query(SectionSubjectTeacher)
            .filter(
                SectionSubjectTeacher.school_id == current_user["school_id"],
                SectionSubjectTeacher.section_id == payload.section_id,
                SectionSubjectTeacher.subject_id == payload.subject_id,
            )
            .first()
        )
        if existing and existing.teacher_id == payload.teacher_id:
            response.status_code = status.HTTP_200_OK
            return existing

        raise HTTPException(status_code=409, detail="assignment_conflict")

    db.refresh(row)
    return row


@router.get("", response_model=List[TeachingAssignmentOut])
def list_teaching_assignments(
    section_id: int | None = Query(None),
    teacher_id: int | None = Query(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    q = db.query(SectionSubjectTeacher).filter(
        SectionSubjectTeacher.school_id == current_user["school_id"]
    )

    if section_id is not None:
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
        q = q.filter(SectionSubjectTeacher.section_id == section_id)

    if teacher_id is not None:
        t = (
            db.query(Teacher)
            .filter(
                Teacher.id == teacher_id,
                Teacher.school_id == current_user["school_id"],
            )
            .first()
        )
        if not t:
            raise HTTPException(status_code=400, detail="invalid_teacher_id")
        q = q.filter(SectionSubjectTeacher.teacher_id == teacher_id)

    return q.order_by(SectionSubjectTeacher.id.asc()).all()
