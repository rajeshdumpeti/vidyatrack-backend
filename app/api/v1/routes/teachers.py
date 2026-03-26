from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.v1.controllers import teachers as teachers_controller
from app.api.v1.deps import get_db, get_current_user, require_management
from app.api.v1.schemas.schools import PaginatedResponse
from app.api.v1.schemas.teachers import TeacherCreate, TeacherOut, TeacherStatusUpdate
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


@router.patch("/{teacher_id}/status", response_model=TeacherOut)
def update_teacher_status(
    teacher_id: int,
    payload: TeacherStatusUpdate,
    school_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_management),
) -> Teacher:
    try:
        return teachers_controller.update_teacher_status(
            db=db,
            teacher_id=teacher_id,
            school_id=school_id,
            status=payload.status,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
