from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.v1.controllers import teachers as teachers_controller
from app.api.v1.deps import get_db, get_current_user
from app.api.v1.schemas.teachers import TeacherCreate, TeacherOut
from app.db.models.teacher import Teacher
from app.db.models.user import User

router = APIRouter(prefix="/teachers", tags=["teachers"])


@router.get("", response_model=List[TeacherOut])
def list_teachers(
    school_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[TeacherOut]:
    return teachers_controller.list_teachers(db=db, school_id=school_id)


@router.post("", response_model=TeacherOut, status_code=201)
def create_teacher(
    payload: TeacherCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Teacher:
    return teachers_controller.create_teacher(db=db, payload=payload)
