from sqlalchemy.orm import Session

from app.api.v1.schemas.classes import ClassCreate
from app.db.models.class_ import Class
from app.services.public_id import get_tenant_code_for_school, next_public_id


def list_classes(*, db: Session, school_id: int) -> list[Class]:
    return db.query(Class).filter(Class.school_id == school_id).all()


def create_class(*, payload: ClassCreate, school_id: int, db: Session) -> Class:
    new_class = Class(
        name=payload.name,
        school_id=school_id,
        public_id=next_public_id(
            db,
            tenant_code=get_tenant_code_for_school(db, school_id),
            entity="class",
        ),
    )
    db.add(new_class)
    db.commit()
    db.refresh(new_class)
    return new_class
