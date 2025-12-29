from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.api.v1.deps import get_db, get_current_user
from app.db.models.class_ import Class

router = APIRouter(prefix="/classes", tags=["classes"])


class ClassCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str


class ClassOut(BaseModel):
    id: int
    school_id: int
    name: str

    class Config:
        from_attributes = True


@router.get("", response_model=List[ClassOut])
def list_classes(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return (
        db.query(Class)
        .filter(Class.school_id == current_user["school_id"])
        .order_by(Class.id.asc())
        .all()
    )


@router.post("", response_model=ClassOut, status_code=201)
def create_class(
    payload: ClassCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    row = Class(
        school_id=current_user["school_id"],
        name=payload.name,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
