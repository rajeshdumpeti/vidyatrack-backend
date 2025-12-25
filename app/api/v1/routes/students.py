from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.api.v1.deps import get_db, get_current_user
from app.db.models.student import Student

router = APIRouter(prefix="/students", tags=["students"])


class StudentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str


class StudentOut(BaseModel):
    id: int
    school_id: int
    name: str

    class Config:
        from_attributes = True


@router.get("", response_model=List[StudentOut])
def list_students(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return (
        db.query(Student)
        .filter(Student.school_id == current_user["school_id"])
        .order_by(Student.id.asc())
        .all()
    )


@router.post("", response_model=StudentOut, status_code=201)
def create_student(
    payload: StudentCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    student = Student(
        school_id=current_user["school_id"],
        name=payload.name,
    )
    db.add(student)
    db.commit()
    db.refresh(student)
    return student
