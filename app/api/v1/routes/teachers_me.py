from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.v1.deps import get_db, require_teacher
from app.db.models.teacher import Teacher
from app.db.models.section_subject_teacher import SectionSubjectTeacher
from app.db.models.section import Section
from app.db.models.class_ import Class
from app.db.models.subject import Subject
from app.db.models.user import User  # keep consistent with your project

router = APIRouter(prefix="/teachers/me", tags=["teachers-me"])


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


@router.get("", response_model=TeacherMeOut)
def get_my_teacher_profile(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_teacher),
):
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

    user = db.query(User).filter(User.id == teacher.user_id).first()

    return TeacherMeOut(
        teacher_id=teacher.id,
        name=teacher.name,
        email=getattr(user, "email", None),
        phone=getattr(user, "phone", None),
    )


@router.get("/teaching-assignments", response_model=list[TeachingAssignmentOut])
def get_my_teaching_assignments(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_teacher),
):
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

    rows = (
        db.query(
            SectionSubjectTeacher.section_id,
            Section.name.label("section_name"),
            Class.id.label("class_id"),
            Class.name.label("class_name"),
            SectionSubjectTeacher.subject_id,
            Subject.name.label("subject_name"),
        )
        .join(
            Section,
            (Section.id == SectionSubjectTeacher.section_id)
            & (Section.school_id == current_user["school_id"]),
        )
        .join(
            Class,
            (Class.id == Section.class_id) & (
                Class.school_id == current_user["school_id"]),
        )
        .join(
            Subject,
            (Subject.id == SectionSubjectTeacher.subject_id)
            & (Subject.school_id == current_user["school_id"]),
        )
        .filter(
            SectionSubjectTeacher.school_id == current_user["school_id"],
            SectionSubjectTeacher.teacher_id == teacher.id,
        )
        .order_by(SectionSubjectTeacher.id.asc())
        .all()
    )

    return [
        TeachingAssignmentOut(
            section_id=r.section_id,
            section_name=r.section_name,
            class_id=r.class_id,
            class_name=r.class_name,
            subject_id=r.subject_id,
            subject_name=r.subject_name,
        )
        for r in rows
    ]
