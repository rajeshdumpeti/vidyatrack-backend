from sqlalchemy.orm import Session

from app.api.v1.schemas.subjects import SubjectCreate
from app.db.models.subject import Subject
from app.services.subjects import create_subject as create_subject_service
from app.services.subjects import list_subjects as list_subjects_service


def list_subjects(*, db: Session, school_id: int) -> list[Subject]:
    return list_subjects_service(db=db, school_id=school_id)


def create_subject(*, db: Session, school_id: int, payload: SubjectCreate) -> Subject:
    return create_subject_service(db=db, school_id=school_id, payload=payload)
