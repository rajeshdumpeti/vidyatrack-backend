from sqlalchemy.orm import Session

from app.db.models.subject import Subject


def list_subjects_for_school(db: Session, *, school_id: int) -> list[Subject]:
    return (
        db.query(Subject)
        .filter(Subject.school_id == school_id)
        .order_by(Subject.id.asc())
        .all()
    )


def get_subject_by_name(db: Session, *, school_id: int, name: str) -> Subject | None:
    return (
        db.query(Subject)
        .filter(
            Subject.school_id == school_id,
            Subject.name == name,
        )
        .first()
    )
