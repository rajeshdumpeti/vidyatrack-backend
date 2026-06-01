from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v1.deps import get_db, require_management
from app.api.v1.schemas.management_schools import ManagementSchoolsOverviewOut
from app.db.models.user import User
from app.services import management_schools as management_schools_service

router = APIRouter(prefix="/management/schools", tags=["management-schools"])


@router.get("", response_model=ManagementSchoolsOverviewOut)
def get_management_schools_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_management),
) -> ManagementSchoolsOverviewOut:
    return management_schools_service.get_management_schools_overview(
        db=db,
        current_user=current_user,
    )
