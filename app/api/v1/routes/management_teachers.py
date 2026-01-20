from __future__ import annotations
import re

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.orm import Session

from app.api.v1.deps import get_db, require_management
from app.core.phone import normalize_phone, phone_candidates
from app.db.models.teacher import Teacher
from app.db.models.teacher_primary_section import TeacherPrimarySection
from app.db.models.section import Section
# keep this import path consistent with your project
from app.db.models.user import User

router = APIRouter(prefix="/management/teachers", tags=["management-teachers"])


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class ManagementCreateTeacherIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200)
    email: str | None = Field(default=None, min_length=5, max_length=255)
    phone: str | None = Field(default=None, min_length=10, max_length=20)
    section_id: int
    # keep if you want, but must NOT be sent; or remove field entirely
    role: str | None = None

    @model_validator(mode="after")
    def validate_contact(self) -> "ManagementCreateTeacherIn":
        # require at least one of email/phone
        if (self.email is None or self.email.strip() == "") and (
            self.phone is None or self.phone.strip() == ""
        ):
            raise ValueError("email_or_phone_required")

        # optional basic email validation
        if self.email is not None:
            e = self.email.strip()
            if not EMAIL_RE.match(e):
                raise ValueError("invalid_email_format")
            self.email = e

        # optional phone normalization (trim only)
        if self.phone is not None:
            self.phone = normalize_phone(self.phone)

        return self


class ManagementCreateTeacherOut(BaseModel):
    user_id: int
    teacher_id: int
    name: str
    email: str | None = None
    phone: str | None = None
    section_id: int

    class Config:
        from_attributes = True


@router.post("", response_model=ManagementCreateTeacherOut, status_code=201)
def management_create_teacher(
    payload: ManagementCreateTeacherIn,
    response: Response,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_management),
):
    school_id = current_user["school_id"]

    section = (
        db.query(Section)
        .filter(Section.school_id == school_id, Section.id == payload.section_id)
        .first()
    )
    if not section:
        raise HTTPException(status_code=400, detail="invalid_section_id")

    # Idempotency lookup: same school + same email OR same phone
    q = db.query(User).filter(User.school_id == school_id)

    candidates = []
    if payload.phone:
        candidates.append(User.phone.in_(phone_candidates(payload.phone)))

    existing_user = None
    if candidates:
        existing_user = q.filter((candidates[0]) if len(
            candidates) == 1 else (candidates[0] | candidates[1])).first()
        if payload.email:
            candidates.append(User.email == payload.email)

    if existing_user:
        # Ensure teacher row exists for this user (pilot: 1 user -> 1 teacher)
        existing_teacher = (
            db.query(Teacher)
            .filter(
                Teacher.school_id == school_id,
                Teacher.user_id == existing_user.id,
            )
            .first()
        )
        if existing_teacher:
            mapping = (
                db.query(TeacherPrimarySection)
                .filter(
                    TeacherPrimarySection.school_id == school_id,
                    TeacherPrimarySection.teacher_id == existing_teacher.id,
                )
                .first()
            )
            if mapping:
                mapping.section_id = payload.section_id
            else:
                mapping = TeacherPrimarySection(
                    school_id=school_id,
                    teacher_id=existing_teacher.id,
                    section_id=payload.section_id,
                )
                db.add(mapping)
            db.commit()
            response.status_code = status.HTTP_200_OK
            return ManagementCreateTeacherOut(
                user_id=existing_user.id,
                teacher_id=existing_teacher.id,
                name=existing_teacher.name,
                email=existing_teacher.email,
                phone=payload.phone,  # phone not stored on Teacher model currently
                section_id=payload.section_id,
            )

        # User exists but teacher missing -> create teacher row (201)
        teacher = Teacher(
            school_id=school_id,
            user_id=existing_user.id,
            name=payload.name,
        )
        db.add(teacher)
        db.flush()

        mapping = TeacherPrimarySection(
            school_id=school_id,
            teacher_id=teacher.id,
            section_id=payload.section_id,
        )
        db.add(mapping)
        db.commit()
        db.refresh(teacher)

        return ManagementCreateTeacherOut(
            user_id=existing_user.id,
            teacher_id=teacher.id,
            name=teacher.name,
            email=teacher.email,
            phone=payload.phone,
            section_id=payload.section_id,
        )

    # Create BOTH: User + Teacher (role forced server-side)
    user = User(
        school_id=school_id,
        role="TEACHER",
        email=payload.email,
        phone=payload.phone,
    )
    db.add(user)
    db.flush()  # get user.id for teacher FK without committing yet

    teacher = Teacher(
        school_id=school_id,
        user_id=user.id,
        name=payload.name,
    )
    db.add(teacher)
    db.flush()

    mapping = TeacherPrimarySection(
        school_id=school_id,
        teacher_id=teacher.id,
        section_id=payload.section_id,
    )
    db.add(mapping)

    db.commit()
    db.refresh(user)
    db.refresh(teacher)

    return ManagementCreateTeacherOut(
        user_id=user.id,
        teacher_id=teacher.id,
        name=teacher.name,
        email=teacher.email,
        phone=payload.phone,
        section_id=payload.section_id,
    )
