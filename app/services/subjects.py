from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.api.v1.schemas.subjects import SubjectCreate
from app.db.models.subject import Subject
from app.db.repositories import subjects as subjects_repository
from app.services.public_id import get_tenant_code_for_school, next_public_id


def list_subjects(*, db: Session, school_id: int) -> list[Subject]:
    return subjects_repository.list_subjects_for_school(db, school_id=school_id)


def create_subject(*, db: Session, school_id: int, payload: SubjectCreate) -> Subject:
    existing = subjects_repository.get_subject_by_name(
        db,
        school_id=school_id,
        name=payload.name,
    )
    if existing:
        raise HTTPException(status_code=400, detail="Subject already exists in this school")

    row = Subject(
        school_id=school_id,
        name=payload.name,
        public_id=next_public_id(
            db,
            tenant_code=get_tenant_code_for_school(db, school_id),
            entity="subject",
        ),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
