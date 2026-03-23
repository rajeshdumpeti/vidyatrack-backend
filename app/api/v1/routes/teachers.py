from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.v1.controllers import teachers as teachers_controller
from app.api.v1.deps import get_db, get_current_user
from app.api.v1.schemas.schools import PaginatedResponse
from app.api.v1.schemas.teachers import TeacherCreate, TeacherOut
from app.db.models.teacher import Teacher
from app.db.models.user import User

router = APIRouter(prefix="/teachers", tags=["teachers"])


@router.get("", response_model=PaginatedResponse[TeacherOut])
def list_teachers(
    school_id: int = Query(...),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginatedResponse[TeacherOut]:
    return teachers_controller.list_teachers_paginated(
        db=db, school_id=school_id, search=search, page=page, limit=limit
    )


@router.post("", response_model=TeacherOut, status_code=201)
def create_teacher(
    payload: TeacherCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Teacher:
    return teachers_controller.create_teacher(db=db, payload=payload)
