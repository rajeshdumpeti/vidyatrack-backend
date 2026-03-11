from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v1.controllers import subjects as subjects_controller
from app.api.v1.deps import get_db, get_current_user
from app.api.v1.schemas.subjects import SubjectCreate, SubjectOut
from app.db.models.subject import Subject
from app.db.models.user import User

router = APIRouter(prefix="/subjects", tags=["subjects"])


@router.get("", response_model=List[SubjectOut])
def list_subjects(
    school_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Subject]:
    return subjects_controller.list_subjects(db=db, school_id=school_id)


@router.post("", response_model=SubjectOut, status_code=201)
def create_subject(
    payload: SubjectCreate,
    school_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Subject:
    return subjects_controller.create_subject(db=db, school_id=school_id, payload=payload)
