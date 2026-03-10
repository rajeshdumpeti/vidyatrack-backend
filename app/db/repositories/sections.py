from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models.class_ import Class
from app.db.models.section import Section


def list_sections_with_class_names(
    db: Session,
    *,
    school_id: int,
    class_id: int | None,
) -> list[tuple[Section, str]]:
    query = db.query(Section).filter(Section.school_id == school_id)

    if class_id:
        query = query.filter(Section.class_id == class_id)

    return (
        query.join(Class, Class.id == Section.class_id)
        .add_columns(Class.name.label("class_name"))
        .order_by(Section.name.asc())
        .all()
    )


def get_class_for_school(db: Session, *, school_id: int, class_id: int) -> Class | None:
    return (
        db.query(Class)
        .filter(
            Class.id == class_id,
            Class.school_id == school_id,
        )
        .first()
    )
