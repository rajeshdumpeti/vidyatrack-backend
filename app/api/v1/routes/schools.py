from typing import List

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.v1.deps import get_db
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
def list_schools(db: Session = Depends(get_db)):
    return db.query(School).order_by(School.id.asc()).all()


@router.post("", response_model=SchoolOut, status_code=201)
def create_school(payload: SchoolCreate, db: Session = Depends(get_db)):
    school = School(name=payload.name)
    db.add(school)
    db.commit()
    db.refresh(school)
    return school
