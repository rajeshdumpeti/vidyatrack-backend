from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.api.v1.deps import get_db, get_current_user
from app.core.phone import normalize_phone, phone_candidates
from app.db.models.teacher import Teacher
from app.db.models.user import User
from app.db.models.section_subject_teacher import SectionSubjectTeacher
from app.db.models.section import Section
from app.db.models.class_ import Class
from app.db.models.subject import Subject
from app.db.models.teacher_primary_section import TeacherPrimarySection

router = APIRouter(prefix="/teachers", tags=["teachers"])

# --- SCHEMAS ---


class TeacherCreate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str
    phone: str = Field(min_length=10, max_length=20)
    email: Optional[str] = None
    school_id: int
    section_id: Optional[int] = None


class TeacherOut(BaseModel):
    id: int
    school_id: int
    user_id: Optional[int] = None
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

# --- ROUTES ---


@router.get("", response_model=List[TeacherOut])
def list_teachers(
    school_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    This was missing! The frontend needs this to display the list.
    """
    teachers = (
        db.query(Teacher)
        .filter(Teacher.school_id == school_id)
        .order_by(Teacher.id.asc())
        .all()
    )
    return teachers


@router.post("", response_model=TeacherOut, status_code=201)
def create_teacher(
    payload: TeacherCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sid = payload.school_id
    normalized_phone = normalize_phone(payload.phone)

    # 1. Resolve User (Multi-school context)
    user = db.query(User).filter(User.phone == normalized_phone).first()
    if not user:
        user = User(
            school_id=sid,
            role="TEACHER",
            phone=normalized_phone,
            email=payload.email,
            is_active=True
        )
        db.add(user)
        db.flush()

    # 2. Resolve Teacher record
    teacher = db.query(Teacher).filter(
        Teacher.school_id == sid,
        Teacher.user_id == user.id
    ).first()

    if not teacher:
        teacher = Teacher(
            school_id=sid,
            user_id=user.id,
            name=payload.name,
            phone=normalized_phone,
            email=payload.email
        )
        db.add(teacher)
        db.flush()

    # 3. Assign Primary Attendance Section
    if payload.section_id:
        db.merge(TeacherPrimarySection(
            school_id=sid,
            teacher_id=teacher.id,
            section_id=payload.section_id
        ))

    db.commit()
    db.refresh(teacher)
    return teacher
