from sqlalchemy.orm import Session

from app.api.v1.schemas.academic_setup import (
    AcademicClassOut,
    AcademicSectionOut,
    AcademicSetupOut,
    AcademicSubjectOut,
)
from app.db.models.class_ import Class
from app.db.models.section import Section
from app.db.models.subject import Subject


def get_academic_setup(*, db: Session, school_id: int) -> AcademicSetupOut:
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
