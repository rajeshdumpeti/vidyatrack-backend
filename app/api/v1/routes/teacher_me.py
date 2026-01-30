from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.v1.deps import get_db, require_teacher
from app.db.models.user import User
from app.db.models.teacher import Teacher
from app.db.models.teacher_primary_section import TeacherPrimarySection
from app.db.models.section import Section
from app.db.models.class_ import Class

router = APIRouter(prefix="/teachers/me", tags=["teachers-me"])


class TeacherAttendanceSectionOut(BaseModel):
    section_id: int
    section_name: str
    class_id: int
    class_name: str


@router.get("/attendance-section", response_model=TeacherAttendanceSectionOut)
def get_attendance_section(
    db: Session = Depends(get_db),
    # Fixed dependency: use User object, not dict
    current_user: User = Depends(require_teacher),
):
    # 1. First, find the Teacher record to discover the school context.
    # We query by user_id because one User = one Teacher profile per school.
    teacher = (
        db.query(Teacher)
        .filter(Teacher.user_id == current_user.id)
        .first()
    )

    if not teacher:
        raise HTTPException(status_code=404, detail="teacher_not_found")

    # 2. Use the Teacher's school_id as the source of truth for the school context.
    sid = teacher.school_id

    # 3. Find the Primary Section assigned to this teacher in this school.
    mapping = (
        db.query(TeacherPrimarySection)
        .filter(
            TeacherPrimarySection.school_id == sid,
            TeacherPrimarySection.teacher_id == teacher.id,
        )
        .first()
    )
    if not mapping:
        raise HTTPException(
            status_code=404, detail="no_primary_section_assigned")

    # 4. Fetch Section and Class details using the discovered school context (sid).
    # This ensures no data leakage between different schools.
    sec = (
        db.query(Section)
        .filter(
            Section.school_id == sid,
            Section.id == mapping.section_id,
        )
        .first()
    )
    if not sec:
        raise HTTPException(status_code=400, detail="invalid_section_id")

    cls = (
        db.query(Class)
        .filter(
            Class.school_id == sid,
            Class.id == sec.class_id,
        )
        .first()
    )
    if not cls:
        raise HTTPException(status_code=400, detail="invalid_class_id")

    return TeacherAttendanceSectionOut(
        section_id=sec.id,
        section_name=sec.name,
        class_id=cls.id,
        class_name=cls.name,
    )
