from sqlalchemy.orm import Session

from app.api.v1.schemas.sections import SectionCreate, SectionOut
from app.db.models.section import Section
from app.services.sections import create_section as create_section_service
from app.services.sections import list_sections as list_sections_service


def list_sections(*, db: Session, school_id: int, class_id: int | None) -> list[SectionOut]:
    return list_sections_service(db=db, school_id=school_id, class_id=class_id)


def create_section(*, db: Session, school_id: int, payload: SectionCreate) -> Section:
    return create_section_service(db=db, school_id=school_id, payload=payload)
