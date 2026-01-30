from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user, get_db, get_valid_school_id, require_management
from app.db.models.section import Section
from app.db.models.subject import Subject
from app.db.models.teacher import Teacher
from app.db.models.section_subject_teacher import SectionSubjectTeacher
from app.db.models.teacher_section_assignment import TeacherSectionAssignment
from app.db.models.user import User

router = APIRouter(prefix="/teaching-assignments",
                   tags=["teaching-assignments"])


class TeachingAssignmentCreate(BaseModel):
    # Removed extra="forbid" to match our Subject fix pattern
    section_id: int
    subject_id: int
    teacher_id: int
    school_id: int


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
    db: Session = Depends(get_db),
    current_user: User = Depends(require_management),
):
    sid = payload.school_id

    # Create the link between Section, Subject, and Teacher
    new_assignment = SectionSubjectTeacher(
        school_id=sid,
        section_id=payload.section_id,
        subject_id=payload.subject_id,
        teacher_id=payload.teacher_id,
    )
    db.add(new_assignment)
    db.commit()
    db.refresh(new_assignment)
    return new_assignment


@router.get("", response_model=List[TeachingAssignmentOut])
def list_teaching_assignments(
    school_id: int,  # Required query param for multi-school isolation
    section_id: int | None = Query(None),
    teacher_id: int | None = Query(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    # Primary filter is always school_id
    q = db.query(SectionSubjectTeacher).filter(
        SectionSubjectTeacher.school_id == school_id
    )

    if section_id is not None:
        q = q.filter(SectionSubjectTeacher.section_id == section_id)

    if teacher_id is not None:
        q = q.filter(SectionSubjectTeacher.teacher_id == teacher_id)

    return q.order_by(SectionSubjectTeacher.id.asc()).all()


@router.get("/my-sections")
def get_my_sections(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    school_id: int = Depends(get_valid_school_id)
):
    """
    Returns the list of sections assigned to the logged-in teacher.
    This allows Rajesh to see '10-A Telugu', '8-A English', etc.
    """
    assignments = db.query(TeacherSectionAssignment).filter(
        TeacherSectionAssignment.teacher_user_id == current_user.id,
        TeacherSectionAssignment.school_id == school_id
    ).all()

    return [
        {
            "section_id": a.section_id,
            "subject_name": a.subject_name,
            "is_primary": a.is_primary_teacher,
            # We will join Section details in the next step to get names like 'Class 10-A'
        } for a in assignments
    ]
