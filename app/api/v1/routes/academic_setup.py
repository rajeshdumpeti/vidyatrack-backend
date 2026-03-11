from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v1.controllers import academic_setup as academic_setup_controller
from app.api.v1.deps import get_current_user, get_db, get_valid_school_id
from app.api.v1.schemas.academic_setup import AcademicSetupOut
from app.db.models.user import User

router = APIRouter(prefix="/academic-setup", tags=["academic-setup"])


@router.get("", response_model=AcademicSetupOut)
def get_academic_setup(
    db: Session = Depends(get_db),
    school_id: int = Depends(get_valid_school_id),
    current_user: User = Depends(get_current_user),
) -> AcademicSetupOut:
    return academic_setup_controller.get_academic_setup(db=db, school_id=school_id)
