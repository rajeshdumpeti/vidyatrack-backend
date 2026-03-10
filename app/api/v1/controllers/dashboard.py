from sqlalchemy.orm import Session

from app.api.v1.schemas.dashboard import ManagementDashboardOut, PrincipalDashboardOut
from app.db.models.user import User
from app.services.dashboard import get_management_dashboard, get_principal_dashboard


def principal_dashboard(*, db: Session, current_user: User) -> PrincipalDashboardOut:
    return get_principal_dashboard(db=db, current_user=current_user)


def management_dashboard(*, db: Session, current_user: User) -> ManagementDashboardOut:
    return get_management_dashboard(db=db, current_user=current_user)
