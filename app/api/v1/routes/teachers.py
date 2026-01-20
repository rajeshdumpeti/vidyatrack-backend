from typing import List, Optional

from fastapi import APIRouter, Depends
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

router = APIRouter(prefix="/teachers", tags=["teachers"])


class TeacherCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    phone: str = Field(min_length=10, max_length=20)
    email: Optional[str] = None


class TeacherOut(BaseModel):
    id: int
    school_id: int
    user_id: Optional[int] = None
    employee_id: Optional[str] = None
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    status: Optional[str] = None
    assignments: List["TeacherAssignmentOut"] = []

    class Config:
        from_attributes = True


class TeacherAssignmentOut(BaseModel):
    class_id: int
    class_name: str
    section_id: int
    section_name: str
    subject_id: int
    subject_name: str
    label: str


@router.get("", response_model=List[TeacherOut])
def list_teachers(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    school_id = current_user["school_id"]
    teachers = (
        db.query(Teacher, User)
        .outerjoin(User, User.id == Teacher.user_id)
        .filter(Teacher.school_id == school_id)
        .order_by(Teacher.id.asc())
        .all()
    )

    teacher_ids = [t.id for t, _ in teachers]
    assignments = []
    if teacher_ids:
        assignments = (
            db.query(
                SectionSubjectTeacher.teacher_id,
                SectionSubjectTeacher.section_id,
                Section.name.label("section_name"),
                Class.id.label("class_id"),
                Class.name.label("class_name"),
                Subject.id.label("subject_id"),
                Subject.name.label("subject_name"),
            )
            .join(
                Section,
                (Section.id == SectionSubjectTeacher.section_id)
                & (Section.school_id == school_id),
            )
            .join(
                Class,
                (Class.id == Section.class_id) & (Class.school_id == school_id),
            )
            .join(
                Subject,
                (Subject.id == SectionSubjectTeacher.subject_id)
                & (Subject.school_id == school_id),
            )
            .filter(
                SectionSubjectTeacher.school_id == school_id,
                SectionSubjectTeacher.teacher_id.in_(teacher_ids),
            )
            .order_by(SectionSubjectTeacher.id.asc())
            .all()
        )

    by_teacher: dict[int, list[TeacherAssignmentOut]] = {}
    for row in assignments:
        by_teacher.setdefault(row.teacher_id, []).append(
            TeacherAssignmentOut(
                class_id=row.class_id,
                class_name=row.class_name,
                section_id=row.section_id,
                section_name=row.section_name,
                subject_id=row.subject_id,
                subject_name=row.subject_name,
                label=f"{row.class_name} {row.subject_name}",
            )
        )

    directory: list[TeacherOut] = []
    for teacher, user in teachers:
        employee_id = f"TE-{teacher.id:04d}"
        status = "active" if user and user.is_active else "inactive"
        directory.append(
            TeacherOut(
                id=teacher.id,
                school_id=teacher.school_id,
                user_id=teacher.user_id,
                employee_id=employee_id,
                name=teacher.name,
                email=(user.email if user and user.email else teacher.email),
                phone=(user.phone if user else None),
                status=status,
                assignments=by_teacher.get(teacher.id, []),
            )
        )

    return directory


@router.post("", response_model=TeacherOut, status_code=201)
def create_teacher(
    payload: TeacherCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    school_id = current_user["school_id"]
    normalized_phone = normalize_phone(payload.phone)
    existing_user = (
        db.query(User)
        .filter(User.school_id == school_id)
        .filter(User.phone.in_(phone_candidates(payload.phone)))
        .first()
    )
    if existing_user:
        teacher = (
            db.query(Teacher)
            .filter(
                Teacher.school_id == school_id,
                Teacher.user_id == existing_user.id,
            )
            .first()
        )
        if teacher:
            return teacher

        teacher = Teacher(
            school_id=school_id,
            user_id=existing_user.id,
            name=payload.name,
            email=payload.email or existing_user.email,
        )
        db.add(teacher)
        db.commit()
        db.refresh(teacher)
        return teacher

    user = User(
        school_id=school_id,
        role="TEACHER",
        phone=normalized_phone,
        email=payload.email,
    )
    db.add(user)
    db.flush()

    teacher = Teacher(
        school_id=school_id,
        user_id=user.id,
        name=payload.name,
        email=payload.email,
    )
    db.add(teacher)
    db.commit()
    db.refresh(teacher)
    return teacher
