from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.v1.deps import get_db, require_teacher
from app.db.models.teacher import Teacher
from app.db.models.teacher_primary_section import TeacherPrimarySection
from app.db.models.section import Section
# adjust import if your class model name differs
from app.db.models.class_ import Class

router = APIRouter(prefix="/teacher/me", tags=["teacher"])


class TeacherAttendanceSectionOut(BaseModel):
    section_id: int
    section_name: str
    class_id: int
    class_name: str


@router.get("/attendance-section", response_model=TeacherAttendanceSectionOut)
def get_attendance_section(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_teacher),
):
    # Resolve Teacher row for this user+school.
    # Mapping: teachers.id == users.id for TEACHER users.
    teacher = (
        db.query(Teacher)
        .filter(
            Teacher.school_id == current_user["school_id"],
            Teacher.user_id == current_user["user_id"],
        )
        .first()
    )
    if not teacher:
        raise HTTPException(status_code=404, detail="teacher_not_found")

    mapping = (
        db.query(TeacherPrimarySection)
        .filter(
            TeacherPrimarySection.school_id == current_user["school_id"],
            TeacherPrimarySection.teacher_id == teacher.id,
        )
        .first()
    )
    if not mapping:
        raise HTTPException(
            status_code=404, detail="no_primary_section_assigned")

    sec = (
        db.query(Section)
        .filter(
            Section.school_id == current_user["school_id"],
            Section.id == mapping.section_id,
        )
        .first()
    )
    if not sec:
        raise HTTPException(status_code=400, detail="invalid_section_id")

    cls = (
        db.query(Class)
        .filter(
            Class.school_id == current_user["school_id"],
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
