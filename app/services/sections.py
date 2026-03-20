from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.api.v1.schemas.sections import SectionCreate, SectionOut
from app.db.models.section import Section
from app.db.repositories import sections as sections_repository
from app.services.public_id import get_tenant_code_for_school, next_public_id


def list_sections(*, db: Session, school_id: int, class_id: int | None) -> list[SectionOut]:
    results = sections_repository.list_sections_with_class_names(
        db,
        school_id=school_id,
        class_id=class_id,
    )

    sections: list[SectionOut] = []
    for section, class_name in results:
        section_out = SectionOut.from_orm(section)
        section_out.class_name = class_name
        sections.append(section_out)

    return sections


def create_section(*, db: Session, school_id: int, payload: SectionCreate) -> Section:
    class_row = sections_repository.get_class_for_school(
        db,
        school_id=school_id,
        class_id=payload.class_id,
    )
    if not class_row:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invalid_class_id",
        )

    row = Section(
        name=payload.name,
        class_id=payload.class_id,
        school_id=school_id,
        public_id=next_public_id(
            db,
            tenant_code=get_tenant_code_for_school(db, school_id),
            entity="section",
        ),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
