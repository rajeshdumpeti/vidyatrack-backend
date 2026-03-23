from typing import Optional

from sqlalchemy.orm import Session

from app.api.v1.schemas.schools import (
    SchoolCreate,
    SchoolDashboardOut,
)
from app.db.models.school import School
from app.db.models.user import User
from app.services import schools as schools_service


def list_schools(
    *, db: Session, search: Optional[str] = None, page: int = 1, limit: int = 25
):
    return schools_service.list_schools(db=db, search=search, page=page, limit=limit)


def get_school_dashboard(*, school_id: int, db: Session) -> SchoolDashboardOut:
    return schools_service.get_school_dashboard(school_id=school_id, db=db)


def get_school_teachers(*, school_id: int, db: Session, page: int = 1, limit: int = 25):
    return schools_service.get_school_teachers(school_id=school_id, db=db, page=page, limit=limit)


def get_school_students(*, school_id: int, db: Session, page: int = 1, limit: int = 25):
    return schools_service.get_school_students(school_id=school_id, db=db, page=page, limit=limit)


def get_school_staff(*, school_id: int, db: Session, page: int = 1, limit: int = 25):
    return schools_service.get_school_staff(school_id=school_id, db=db, page=page, limit=limit)


def create_school(
    *, payload: SchoolCreate, db: Session, current_user: User, idempotency_key: Optional[str] = None
) -> School:
    return schools_service.create_school(
        payload=payload, db=db, current_user=current_user, idempotency_key=idempotency_key
    )
