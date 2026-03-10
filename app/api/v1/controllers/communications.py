from sqlalchemy.orm import Session

from app.api.v1.schemas.communications import (
    HomeworkCreate,
    HomeworkOut,
    ParentMessageCreate,
    ParentMessageOut,
)
from app.db.models.user import User
from app.services import communications as communications_service


def create_homework(
    *,
    payload: HomeworkCreate,
    db: Session,
    current_user: User,
    school_id: int,
) -> HomeworkOut:
    return communications_service.create_homework(
        payload=payload,
        db=db,
        current_user=current_user,
        school_id=school_id,
    )


def list_homework(
    *,
    school_id: int,
    section_id: int | None,
    subject_id: int | None,
    db: Session,
    current_user: User,
) -> list[HomeworkOut]:
    return communications_service.list_homework(
        school_id=school_id,
        section_id=section_id,
        subject_id=subject_id,
        db=db,
        current_user=current_user,
    )


def create_parent_message(
    *,
    payload: ParentMessageCreate,
    db: Session,
    current_user: User,
    school_id: int,
) -> ParentMessageOut:
    return communications_service.create_parent_message(
        payload=payload,
        db=db,
        current_user=current_user,
        school_id=school_id,
    )


def list_parent_messages(
    *,
    school_id: int,
    section_id: int | None,
    db: Session,
    current_user: User,
) -> list[ParentMessageOut]:
    return communications_service.list_parent_messages(
        school_id=school_id,
        section_id=section_id,
        db=db,
        current_user=current_user,
    )
