from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.api.v1.deps import get_db, get_current_user
from app.db.models.subject import Subject

router = APIRouter(prefix="/subjects", tags=["subjects"])


class SubjectCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str


class SubjectOut(BaseModel):
    id: int
    school_id: int
    name: str

    class Config:
        from_attributes = True


@router.get("", response_model=List[SubjectOut])
def list_subjects(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return (
        db.query(Subject)
        .filter(Subject.school_id == current_user["school_id"])
        .order_by(Subject.id.asc())
        .all()
    )


@router.post("", response_model=SubjectOut, status_code=201)
def create_subject(
    payload: SubjectCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    row = Subject(
        school_id=current_user["school_id"],
        name=payload.name,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
