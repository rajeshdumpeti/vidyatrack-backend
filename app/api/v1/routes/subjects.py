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
    school_id: int  # Add this so Pydantic accepts it in the JSON body


class SubjectOut(BaseModel):
    id: int
    school_id: int
    name: str

    class Config:
        from_attributes = True


@router.get("", response_model=List[SubjectOut])
def list_subjects(
    school_id: int,  # Context from frontend
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return (
        db.query(Subject)
        .filter(Subject.school_id == school_id)
        .order_by(Subject.id.asc())
        .all()
    )


@router.post("", response_model=SubjectOut, status_code=201)
def create_subject(
    payload: SubjectCreate,
    school_id: int,  # This must match the query param ?school_id=15 from your screenshot
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    # Verify the subject doesn't already exist for this school to prevent 500 errors
    existing = db.query(Subject).filter(
        Subject.school_id == school_id,
        Subject.name == payload.name
    ).first()

    if existing:
        # Returning a clear error prevents the generic "Please try again" message
        from fastapi import HTTPException
        raise HTTPException(
            status_code=400, detail="Subject already exists in this school")

    row = Subject(
        school_id=school_id,
        name=payload.name,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
