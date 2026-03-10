from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v1.controllers import dashboard as dashboard_controller
from app.api.v1.deps import get_db, require_management
from app.api.v1.schemas.dashboard import ManagementDashboardOut
from app.db.models.user import User

router = APIRouter(prefix="/management/dashboard",
                   tags=["management-dashboard"])


@router.get("", response_model=ManagementDashboardOut)
def get_management_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_management),
) -> ManagementDashboardOut:
    return dashboard_controller.management_dashboard(db=db, current_user=current_user)
