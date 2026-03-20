from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.v1.controllers import communications as communications_controller
from app.api.v1.deps import get_db, get_valid_school_id, require_teacher_or_principal
from app.api.v1.schemas.communications import (
    HomeworkCreate,
    HomeworkOut,
    ParentMessageCreate,
    ParentMessageOut,
)
from app.db.models.user import User

router = APIRouter(prefix="/communications", tags=["communications"])

@router.post("/homework", response_model=HomeworkOut, status_code=201)
def create_homework(
    payload: HomeworkCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_principal),
    school_id: int = Depends(get_valid_school_id),
) -> HomeworkOut:
    return communications_controller.create_homework(
        payload=payload,
        db=db,
        current_user=current_user,
        school_id=school_id,
    )


@router.get("/homework", response_model=List[HomeworkOut])
def list_homework(
    school_id: int = Depends(get_valid_school_id),
    section_id: int | None = Query(None),
    subject_id: int | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_principal),
) -> list[HomeworkOut]:
    return communications_controller.list_homework(
        school_id=school_id,
        section_id=section_id,
        subject_id=subject_id,
        db=db,
        current_user=current_user,
    )


@router.post("/parent-messages", response_model=ParentMessageOut, status_code=201)
def create_parent_message(
    payload: ParentMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_principal),
    school_id: int = Depends(get_valid_school_id),
) -> ParentMessageOut:
    return communications_controller.create_parent_message(
        payload=payload,
        db=db,
        current_user=current_user,
        school_id=school_id,
    )


@router.get("/parent-messages", response_model=List[ParentMessageOut])
def list_parent_messages(
    school_id: int = Depends(get_valid_school_id),
    section_id: int | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_principal),
) -> list[ParentMessageOut]:
    return communications_controller.list_parent_messages(
        school_id=school_id,
        section_id=section_id,
        db=db,
        current_user=current_user,
    )
