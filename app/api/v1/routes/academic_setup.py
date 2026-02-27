from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user, get_db, get_valid_school_id
from app.db.models.class_ import Class
from app.db.models.section import Section
from app.db.models.subject import Subject
from app.db.models.user import User

router = APIRouter(prefix="/academic-setup", tags=["academic-setup"])


class AcademicClassOut(BaseModel):
    id: int
    name: str


class AcademicSectionOut(BaseModel):
    id: int
    name: str
    class_id: int
    class_name: str | None = None


class AcademicSubjectOut(BaseModel):
    id: int
    name: str


class AcademicSetupOut(BaseModel):
    school_id: int
    classes: list[AcademicClassOut]
    sections: list[AcademicSectionOut]
    subjects: list[AcademicSubjectOut]


@router.get("", response_model=AcademicSetupOut)
def get_academic_setup(
    db: Session = Depends(get_db),
    school_id: int = Depends(get_valid_school_id),
    current_user: User = Depends(get_current_user),
):
    classes = (
        db.query(Class)
        .filter(Class.school_id == school_id)
        .order_by(Class.name.asc())
        .all()
    )

    section_rows = (
        db.query(
            Section.id.label("id"),
            Section.name.label("name"),
            Section.class_id.label("class_id"),
            Class.name.label("class_name"),
        )
        .join(Class, Class.id == Section.class_id)
        .filter(Section.school_id == school_id, Class.school_id == school_id)
        .order_by(Class.name.asc(), Section.name.asc())
        .all()
    )

    subjects = (
        db.query(Subject)
        .filter(Subject.school_id == school_id)
        .order_by(Subject.name.asc())
        .all()
    )

    return AcademicSetupOut(
        school_id=school_id,
        classes=[AcademicClassOut(id=row.id, name=row.name) for row in classes],
        sections=[
            AcademicSectionOut(
                id=row.id,
                name=row.name,
                class_id=row.class_id,
                class_name=row.class_name,
            )
            for row in section_rows
        ],
        subjects=[AcademicSubjectOut(id=row.id, name=row.name) for row in subjects],
    )

