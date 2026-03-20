from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.api.v1.controllers import management_teachers as management_teachers_controller
from app.api.v1.deps import get_db, require_management
from app.api.v1.schemas.management_teachers import (
    ManagementCreateTeacherIn,
    ManagementCreateTeacherOut,
)
from app.db.models.user import User

router_mgmt = APIRouter(prefix="/management/teachers",
                        tags=["management-teachers"])


@router_mgmt.post("", response_model=ManagementCreateTeacherOut, status_code=201)
def management_create_teacher(
    payload: ManagementCreateTeacherIn,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_management),
) -> ManagementCreateTeacherOut:
    return management_teachers_controller.management_create_teacher(
        payload=payload,
        response=response,
        db=db,
    )


# Required to maintain compatibility with your app/api/v1/router.py
router = router_mgmt
