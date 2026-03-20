from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v1.controllers import classes as classes_controller
from app.api.v1.deps import get_db, get_current_user
from app.api.v1.schemas.classes import ClassCreate, ClassOut
from app.db.models.class_ import Class

router = APIRouter(prefix="/classes", tags=["classes"])


@router.get("", response_model=List[ClassOut])
def list_classes(
    school_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> list[Class]:
    return classes_controller.list_classes(school_id=school_id, db=db)


@router.post("", response_model=ClassOut, status_code=201)
def create_class(
    payload: ClassCreate,
    school_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> Class:
    return classes_controller.create_class(payload=payload, school_id=school_id, db=db)
