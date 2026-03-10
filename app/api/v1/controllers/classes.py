from sqlalchemy.orm import Session

from app.api.v1.schemas.classes import ClassCreate
from app.db.models.class_ import Class
from app.services import classes as classes_service


def list_classes(*, school_id: int, db: Session) -> list[Class]:
    return classes_service.list_classes(school_id=school_id, db=db)


def create_class(*, payload: ClassCreate, school_id: int, db: Session) -> Class:
    return classes_service.create_class(payload=payload, school_id=school_id, db=db)
