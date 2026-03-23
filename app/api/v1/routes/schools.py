from typing import List, Optional

from fastapi import APIRouter, Depends, Header, Request, Response
from sqlalchemy.orm import Session

from app.api.v1.controllers import schools as schools_controller
from app.api.v1.deps import get_db, get_current_user, require_super_admin
from app.api.v1.schemas.schools import (
    SchoolCreate,
    SchoolDashboardOut,
    SchoolOut,
    SchoolStaffListItem,
    SchoolStudentListItem,
    SchoolTeacherListItem,
)
from app.db.models.school import School
from app.db.models.user import User

router = APIRouter(prefix="/schools", tags=["schools"])


@router.get("", response_model=List[SchoolOut])
def list_schools(
    db: Session = Depends(get_db),
    _current_user: dict = Depends(get_current_user),
) -> list[SchoolOut]:
    return schools_controller.list_schools(db=db)


@router.get("/{school_id}/dashboard", response_model=SchoolDashboardOut)
def get_school_dashboard(
    school_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_super_admin),
) -> SchoolDashboardOut:
    return schools_controller.get_school_dashboard(school_id=school_id, db=db)


@router.get("/{school_id}/teachers", response_model=List[SchoolTeacherListItem])
def get_school_teachers(
    school_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_super_admin),
) -> list[SchoolTeacherListItem]:
    return schools_controller.get_school_teachers(school_id=school_id, db=db)


@router.get("/{school_id}/students", response_model=List[SchoolStudentListItem])
def get_school_students(
    school_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_super_admin),
) -> list[SchoolStudentListItem]:
    return schools_controller.get_school_students(school_id=school_id, db=db)


@router.get("/{school_id}/staff", response_model=List[SchoolStaffListItem])
def get_school_staff(
    school_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_super_admin),
) -> list[SchoolStaffListItem]:
    return schools_controller.get_school_staff(school_id=school_id, db=db)


@router.post("", response_model=SchoolOut, status_code=201)
def create_school(
    payload: SchoolCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
) -> School:
    return schools_controller.create_school(
        payload=payload,
        db=db,
        current_user=current_user,
        idempotency_key=idempotency_key,
    )
