from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.v1.deps import get_db, require_management
from app.api.v1.schemas.management_settings import (
    ManagedUserPasswordResetOut,
    NotificationPreferenceOut,
    NotificationPreferenceUpdateIn,
)
from app.db.models.user import User
from app.services import management_settings as management_settings_service

router = APIRouter(prefix="/management/settings", tags=["management-settings"])


@router.get("/notifications", response_model=NotificationPreferenceOut)
def get_notifications(
    school_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_management),
) -> NotificationPreferenceOut:
    return management_settings_service.get_notification_preferences(
        db,
        school_id=school_id,
        current_user=current_user,
    )


@router.patch("/notifications", response_model=NotificationPreferenceOut)
def update_notifications(
    payload: NotificationPreferenceUpdateIn,
    school_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_management),
) -> NotificationPreferenceOut:
    return management_settings_service.update_notification_preferences(
        db,
        school_id=school_id,
        payload=payload,
        current_user=current_user,
    )


@router.post("/users/{user_id}/reset-password", response_model=ManagedUserPasswordResetOut)
def reset_user_password(
    user_id: int,
    school_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_management),
) -> ManagedUserPasswordResetOut:
    return management_settings_service.reset_managed_user_password(
        db,
        school_id=school_id,
        user_id=user_id,
        current_user=current_user,
    )


@router.get("/export/students.csv")
def export_students(
    school_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_management),
) -> Response:
    csv_text = management_settings_service.export_students_csv(
        db,
        school_id=school_id,
        current_user=current_user,
    )
    return Response(content=csv_text, media_type="text/csv")
