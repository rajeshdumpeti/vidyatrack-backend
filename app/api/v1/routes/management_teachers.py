from __future__ import annotations
import re
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.api.v1.deps import get_db, require_management
from app.core.phone import normalize_phone, phone_candidates
from app.db.models.teacher import Teacher
from app.db.models.teacher_primary_section import TeacherPrimarySection
from app.db.models.section import Section
from app.db.models.user import User

router_mgmt = APIRouter(prefix="/management/teachers",
                        tags=["management-teachers"])
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# --- SCHEMAS ---


class ManagementCreateTeacherIn(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str = Field(min_length=1, max_length=200)
    email: str | None = Field(default=None, min_length=5, max_length=255)
    phone: str | None = Field(default=None, min_length=10, max_length=20)
    section_id: int
    school_id: int  # Mandatory from payload since User model doesn't store it

    @model_validator(mode="after")
    def validate_contact(self) -> "ManagementCreateTeacherIn":
        if not self.email and not self.phone:
            raise ValueError("email_or_phone_required")
        if self.email:
            self.email = self.email.strip()
            if not EMAIL_RE.match(self.email):
                raise ValueError("invalid_email_format")
        if self.phone:
            self.phone = normalize_phone(self.phone)
        return self


class ManagementCreateTeacherOut(BaseModel):
    user_id: int
    teacher_id: int
    name: str
    email: str | None = None
    phone: str | None = None
    section_id: int
    model_config = ConfigDict(from_attributes=True)

# --- ROUTES ---


@router_mgmt.post("", response_model=ManagementCreateTeacherOut, status_code=201)
def management_create_teacher(
    payload: ManagementCreateTeacherIn,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_management),
):
    # Trust the school_id from payload since User is multi-school
    sid = payload.school_id

    # 1. Validate Section
    section = (
        db.query(Section)
        .filter(Section.school_id == sid, Section.id == payload.section_id)
        .first()
    )
    if not section:
        raise HTTPException(status_code=400, detail="invalid_section_id")

    # 2. Idempotency Check: Find existing user by phone
    # Note: Using global phone lookup as phone is unique in your User model
    existing_user = (
        db.query(User)
        .filter(User.phone.in_(phone_candidates(payload.phone)))
        .first()
    )

    teacher = None
    if existing_user:
        # Check if they are already a teacher in THIS school
        teacher = (
            db.query(Teacher)
            .filter(Teacher.school_id == sid, Teacher.user_id == existing_user.id)
            .first()
        )

        if teacher:
            # Update primary section if they already exist
            mapping = db.query(TeacherPrimarySection).filter(
                TeacherPrimarySection.teacher_id == teacher.id,
                TeacherPrimarySection.school_id == sid
            ).first()

            if mapping:
                mapping.section_id = payload.section_id
            else:
                db.add(TeacherPrimarySection(school_id=sid,
                       teacher_id=teacher.id, section_id=payload.section_id))

            db.commit()
            response.status_code = status.HTTP_200_OK
            return ManagementCreateTeacherOut(
                user_id=existing_user.id,
                teacher_id=teacher.id,
                name=teacher.name,
                email=existing_user.email,
                phone=existing_user.phone,
                section_id=payload.section_id
            )

    # 3. Create New User if needed
    if not existing_user:
        new_user = User(
            role="TEACHER",
            phone=payload.phone,
            email=payload.email,
            is_active=True
        )
        db.add(new_user)
        db.flush()
        existing_user = new_user

    # 4. Create Teacher record
    if not teacher:
        teacher = Teacher(
            school_id=sid,
            user_id=existing_user.id,
            name=payload.name,
        )
        db.add(teacher)
        db.flush()

    # 5. Create Primary Section Mapping
    mapping = TeacherPrimarySection(
        school_id=sid,
        teacher_id=teacher.id,
        section_id=payload.section_id
    )
    db.add(mapping)

    db.commit()
    db.refresh(teacher)

    return ManagementCreateTeacherOut(
        user_id=existing_user.id,
        teacher_id=teacher.id,
        name=teacher.name,
        email=existing_user.email,
        phone=existing_user.phone,
        section_id=payload.section_id
    )


# Required to maintain compatibility with your app/api/v1/router.py
router = router_mgmt
