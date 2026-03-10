from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v1.controllers import dashboard as dashboard_controller
from app.api.v1.deps import get_db, require_principal
from app.api.v1.schemas.dashboard import PrincipalDashboardOut
from app.db.models.user import User

router = APIRouter(prefix="/principal/dashboard",
                   tags=["principal-dashboard"])


@router.get("", response_model=PrincipalDashboardOut)
def get_principal_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_principal),
) -> PrincipalDashboardOut:
    return dashboard_controller.principal_dashboard(db=db, current_user=current_user)
