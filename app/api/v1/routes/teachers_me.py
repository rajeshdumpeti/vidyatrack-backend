from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.v1.deps import get_db, require_teacher
from app.db.models.teacher import Teacher
from app.db.models.teacher_primary_section import TeacherPrimarySection
from app.db.models.section_subject_teacher import SectionSubjectTeacher
from app.db.models.section import Section
from app.db.models.class_ import Class
from app.db.models.subject import Subject
from app.db.models.user import User

router = APIRouter(prefix="/teachers/me", tags=["teachers-me"])

# --- SCHEMAS ---


class TeacherMeOut(BaseModel):
    teacher_id: int
    name: str
    email: str | None = None
    phone: str | None = None


class TeachingAssignmentOut(BaseModel):
    section_id: int
    section_name: str
    class_id: int
    class_name: str
    subject_id: int
    subject_name: str


class TeacherAttendanceSectionOut(BaseModel):
    section_id: int
    section_name: str
    class_id: int
    class_name: str

# --- ROUTES ---


@router.get("", response_model=TeacherMeOut)
def get_my_teacher_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher),
):
    # Lookup the teacher record via the User ID
    teacher = db.query(Teacher).filter(
        Teacher.user_id == current_user.id).first()
    if not teacher:
        raise HTTPException(status_code=404, detail="teacher_not_found")

    return TeacherMeOut(
        teacher_id=teacher.id,
        name=teacher.name,
        email=current_user.email,
        phone=current_user.phone,
    )


@router.get("/teaching-assignments", response_model=list[TeachingAssignmentOut])
def get_my_teaching_assignments(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher),
):
    # Find teacher to get their school context (sid)
    teacher = db.query(Teacher).filter(
        Teacher.user_id == current_user.id).first()
    if not teacher:
        raise HTTPException(status_code=404, detail="teacher_not_found")

    sid = teacher.school_id

    # JOIN assignments with Section, Class, and Subject for the UI labels
    rows = (
        db.query(
            SectionSubjectTeacher.section_id,
            Section.name.label("section_name"),
            Class.id.label("class_id"),
            Class.name.label("class_name"),
            SectionSubjectTeacher.subject_id,
            Subject.name.label("subject_name"),
        )
        .join(Section, Section.id == SectionSubjectTeacher.section_id)
        .join(Class, Class.id == Section.class_id)
        .join(Subject, Subject.id == SectionSubjectTeacher.subject_id)
        .filter(
            SectionSubjectTeacher.teacher_id == teacher.id,
            SectionSubjectTeacher.school_id == sid
        )
        .all()
    )
    return [TeachingAssignmentOut(**r._asdict()) for r in rows]


@router.get("/attendance-section", response_model=TeacherAttendanceSectionOut)
def get_my_attendance_section(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher),
):
    teacher = db.query(Teacher).filter(
        Teacher.user_id == current_user.id).first()
    if not teacher:
        raise HTTPException(status_code=404, detail="teacher_not_found")

    sid = teacher.school_id

    # Find the primary section for the "Mark Attendance" button context
    mapping = db.query(TeacherPrimarySection).filter(
        TeacherPrimarySection.teacher_id == teacher.id,
        TeacherPrimarySection.school_id == sid
    ).first()

    if not mapping:
        raise HTTPException(
            status_code=404, detail="no_primary_section_assigned")

    res = (
        db.query(
            Section.id.label("section_id"),
            Section.name.label("section_name"),
            Class.id.label("class_id"),
            Class.name.label("class_name")
        )
        .join(Class, Class.id == Section.class_id)
        .filter(Section.id == mapping.section_id, Section.school_id == sid)
        .first()
    )

    if not res:
        raise HTTPException(
            status_code=404, detail="section_details_not_found")

    return TeacherAttendanceSectionOut(
        section_id=res.section_id,
        section_name=res.section_name,
        class_id=res.class_id,
        class_name=res.class_name
    )
