from fastapi import Response
from sqlalchemy.orm import Session

from app.api.v1.schemas.management_teachers import (
    ManagementCreateTeacherIn,
    ManagementCreateTeacherOut,
)
from app.services import management_teachers as management_teachers_service


def management_create_teacher(
    *,
    payload: ManagementCreateTeacherIn,
    response: Response,
    db: Session,
) -> ManagementCreateTeacherOut:
    return management_teachers_service.management_create_teacher(
        payload=payload,
        response=response,
        db=db,
    )
