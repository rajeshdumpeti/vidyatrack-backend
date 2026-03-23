from sqlalchemy.orm import Session

from app.api.v1.schemas.schools import PaginatedResponse
from app.api.v1.schemas.teachers import TeacherCreate, TeacherOut
from app.db.models.teacher import Teacher
from app.services.teachers import create_teacher as create_teacher_service
from app.services.teachers import list_teachers as list_teachers_service
from app.services.teachers import list_teachers_paginated as list_teachers_paginated_service


def list_teachers(*, db: Session, school_id: int) -> list[TeacherOut]:
    return list_teachers_service(db=db, school_id=school_id)


def list_teachers_paginated(
    *,
    db: Session,
    school_id: int,
    search: str | None = None,
    page: int = 1,
    limit: int = 25,
) -> PaginatedResponse[TeacherOut]:
    return list_teachers_paginated_service(
        db=db, school_id=school_id, search=search, page=page, limit=limit
    )


def create_teacher(*, db: Session, payload: TeacherCreate) -> Teacher:
    return create_teacher_service(db=db, payload=payload)
