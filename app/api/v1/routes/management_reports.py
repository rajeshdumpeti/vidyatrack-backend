from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.v1.deps import get_db, require_management
from app.api.v1.schemas.management_reports import ManagementReportsOut
from app.db.models.user import User
from app.services import management_reports as management_reports_service

router = APIRouter(prefix="/management/reports", tags=["management-reports"])


@router.get("", response_model=ManagementReportsOut)
def get_management_reports(
    school_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_management),
) -> ManagementReportsOut:
    return management_reports_service.get_management_reports(
        db,
        school_id=school_id,
        current_user=current_user,
    )
