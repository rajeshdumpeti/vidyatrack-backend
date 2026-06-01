from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.v1.controllers import dashboard as dashboard_controller
from app.api.v1.deps import get_db, require_management
from app.api.v1.schemas.dashboard import (
    ManagementDashboardAlertActionIn,
    ManagementDashboardAlertActionOut,
    ManagementDashboardAlertHistoryOut,
    ManagementDashboardOut,
)
from app.db.models.user import User

router = APIRouter(prefix="/management/dashboard",
                   tags=["management-dashboard"])


@router.get("", response_model=ManagementDashboardOut)
def get_management_dashboard(
    school_id: int | None = Query(default=None),
    academic_year: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_management),
) -> ManagementDashboardOut:
    return dashboard_controller.management_dashboard(
        db=db,
        current_user=current_user,
        school_id=school_id,
        academic_year=academic_year,
    )


@router.post("/alerts/action", response_model=ManagementDashboardAlertActionOut)
def post_management_alert_action(
    payload: ManagementDashboardAlertActionIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_management),
) -> ManagementDashboardAlertActionOut:
    return dashboard_controller.management_alert_action(
        db=db,
        current_user=current_user,
        alert_type=payload.alert_type,
        action_type=payload.action_type,
        school_id=payload.school_id,
    )


@router.get("/alerts/history", response_model=ManagementDashboardAlertHistoryOut)
def get_management_alert_history(
    school_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_management),
) -> ManagementDashboardAlertHistoryOut:
    return dashboard_controller.management_alert_history(
        db=db,
        current_user=current_user,
        school_id=school_id,
    )
