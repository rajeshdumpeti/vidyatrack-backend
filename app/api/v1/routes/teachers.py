from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.api.v1.deps import get_db, get_current_user
from app.db.models.teacher import Teacher

router = APIRouter(prefix="/teachers", tags=["teachers"])


class TeacherCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    email: Optional[str] = None


class TeacherOut(BaseModel):
    id: int
    school_id: int
    name: str
    email: Optional[str] = None

    class Config:
        from_attributes = True


@router.get("", response_model=List[TeacherOut])
def list_teachers(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return (
        db.query(Teacher)
        .filter(Teacher.school_id == current_user["school_id"])
        .order_by(Teacher.id.asc())
        .all()
    )


@router.post("", response_model=TeacherOut, status_code=201)
def create_teacher(
    payload: TeacherCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    teacher = Teacher(
        school_id=current_user["school_id"],
        name=payload.name,
        email=payload.email,
    )
    db.add(teacher)
    db.commit()
    db.refresh(teacher)
    return teacher
