from sqlalchemy.orm import Session

from app.api.v1.schemas.dashboard import (
    ManagementDashboardAlertActionOut,
    ManagementDashboardAlertHistoryOut,
    ManagementDashboardOut,
    PrincipalDashboardOut,
)
from app.db.models.user import User
from app.services.dashboard import (
    get_management_alert_history,
    get_management_dashboard,
    get_principal_dashboard,
    log_management_alert_action,
)


def principal_dashboard(*, db: Session, current_user: User) -> PrincipalDashboardOut:
    return get_principal_dashboard(db=db, current_user=current_user)


def management_dashboard(
    *,
    db: Session,
    current_user: User,
    school_id: int | None = None,
    academic_year: str | None = None,
) -> ManagementDashboardOut:
    return get_management_dashboard(
        db=db,
        current_user=current_user,
        school_id=school_id,
        academic_year=academic_year,
    )


def management_alert_action(
    *,
    db: Session,
    current_user: User,
    alert_type: str,
    action_type: str,
    school_id: int | None = None,
) -> ManagementDashboardAlertActionOut:
    return log_management_alert_action(
        db=db,
        current_user=current_user,
        alert_type=alert_type,
        action_type=action_type,
        school_id=school_id,
    )


def management_alert_history(
    *,
    db: Session,
    current_user: User,
    school_id: int | None = None,
) -> ManagementDashboardAlertHistoryOut:
    return get_management_alert_history(
        db=db,
        current_user=current_user,
        school_id=school_id,
    )
