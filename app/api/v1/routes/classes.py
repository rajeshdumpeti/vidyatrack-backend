from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.api.v1.deps import get_db, get_current_user, get_valid_school_id
from app.db.models.class_ import Class
from app.db.models.user_school import UserSchool
from app.services.public_id import get_tenant_code_for_school, next_public_id

router = APIRouter(prefix="/classes", tags=["classes"])


class ClassCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str


class ClassOut(BaseModel):
    id: int
    public_id: str
    school_id: int
    name: str

    class Config:
        from_attributes = True


@router.get("", response_model=List[ClassOut])
def list_classes(
    school_id: int,  # Injecting from query param for multi-school support
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    # Filter by the school_id parameter passed from the frontend
    return db.query(Class).filter(Class.school_id == school_id).all()


@router.post("", response_model=ClassOut, status_code=201)
def create_class(
    payload: ClassCreate,
    school_id: int,  # Get from query parameter
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    new_class = Class(
        name=payload.name,
        school_id=school_id,
        public_id=next_public_id(
            db,
            tenant_code=get_tenant_code_for_school(db, school_id),
            entity="class",
        ),
    )
    db.add(new_class)
    db.commit()
    db.refresh(new_class)
    return new_class
