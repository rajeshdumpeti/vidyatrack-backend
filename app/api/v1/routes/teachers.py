from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.api.v1.deps import get_db, get_current_user
from app.core.phone import normalize_phone
from app.db.models.teacher import Teacher
from app.db.models.user import User
from app.db.models.section_subject_teacher import SectionSubjectTeacher
from app.db.models.section import Section
from app.db.models.class_ import Class
from app.db.models.subject import Subject
from app.db.models.teacher_primary_section import TeacherPrimarySection
from app.db.models.user_school import UserSchool

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
    employee_id: Optional[str] = None
    status: Optional[str] = None
    assigned_section_label: Optional[str] = None
    assignments: list[dict] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True)

# --- ROUTES ---


@router.get("", response_model=List[TeacherOut])
def list_teachers(
    school_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    teachers = (
        db.query(Teacher)
        .filter(Teacher.school_id == school_id)
        .order_by(Teacher.id.asc())
        .all()
    )

    teacher_ids = [teacher.id for teacher in teachers]
    user_ids = [teacher.user_id for teacher in teachers if teacher.user_id]

    users_by_id = {
        user.id: user
        for user in db.query(User).filter(User.id.in_(user_ids)).all()
    } if user_ids else {}

    primary_section_rows = (
        db.query(
            TeacherPrimarySection.teacher_id,
            Class.name.label("class_name"),
            Section.name.label("section_name"),
        )
        .join(Section, Section.id == TeacherPrimarySection.section_id)
        .join(Class, Class.id == Section.class_id)
        .filter(
            TeacherPrimarySection.school_id == school_id,
            TeacherPrimarySection.teacher_id.in_(teacher_ids),
        )
        .all()
    ) if teacher_ids else []

    assigned_section_by_teacher = {
        row.teacher_id: f"{row.class_name} - {row.section_name}"
        for row in primary_section_rows
    }

    assignment_rows = (
        db.query(
            SectionSubjectTeacher.teacher_id,
            Subject.name.label("subject_name"),
            Class.name.label("class_name"),
            Section.name.label("section_name"),
        )
        .join(Section, Section.id == SectionSubjectTeacher.section_id)
        .join(Class, Class.id == Section.class_id)
        .join(Subject, Subject.id == SectionSubjectTeacher.subject_id)
        .filter(
            SectionSubjectTeacher.school_id == school_id,
            SectionSubjectTeacher.teacher_id.in_(teacher_ids),
        )
        .all()
    ) if teacher_ids else []

    assignments_by_teacher: dict[int, list[dict]] = {}
    for row in assignment_rows:
        assignments_by_teacher.setdefault(row.teacher_id, []).append(
            {"label": f"{row.subject_name} • {row.class_name}-{row.section_name}"}
        )

    return [
        TeacherOut(
            id=teacher.id,
            school_id=teacher.school_id,
            user_id=teacher.user_id,
            name=teacher.name,
            email=(
                teacher.email
                or (
                    users_by_id[teacher.user_id].email
                    if teacher.user_id in users_by_id
                    else None
                )
            ),
            phone=users_by_id.get(teacher.user_id).phone
            if teacher.user_id in users_by_id
            else None,
            employee_id=f"T-{teacher.id:04d}",
            status=(
                "active"
                if (
                    teacher.user_id not in users_by_id
                    or users_by_id[teacher.user_id].is_active
                )
                else "inactive"
            ),
            assigned_section_label=assigned_section_by_teacher.get(teacher.id),
            assignments=assignments_by_teacher.get(teacher.id, []),
        )
        for teacher in teachers
    ]


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
            email=payload.email
        )
        db.add(teacher)
        db.flush()

    user_school = (
        db.query(UserSchool)
        .filter(UserSchool.user_id == user.id, UserSchool.school_id == sid)
        .first()
    )
    if not user_school:
        db.add(UserSchool(user_id=user.id, school_id=sid, role="teacher"))

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
