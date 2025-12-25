from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.v1.deps import get_db, get_current_user
from app.db.models.school import School

router = APIRouter(prefix="/schools", tags=["schools"])


class SchoolCreate(BaseModel):
    name: str


class SchoolOut(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True  # allow returning SQLAlchemy ORM objects


@router.get("", response_model=List[SchoolOut])
def list_schools(
    db: Session = Depends(get_db),
    _current_user: dict = Depends(get_current_user),

):
    return db.query(School).order_by(School.id.asc()).all()


@router.post("", response_model=SchoolOut, status_code=201)
def create_school(
    payload: SchoolCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    if current_user["role"] != "MANAGEMENT":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="insufficient_permissions",
        )

    school = School(name=payload.name)
    db.add(school)
    db.commit()
    db.refresh(school)
    return school
