from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.api.v1.deps import get_db, get_current_user
from app.db.models.class_ import Class
from app.db.models.section import Section

router = APIRouter(prefix="/sections", tags=["sections"])


class SectionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    class_id: int
    name: str


class SectionOut(BaseModel):
    id: int
    school_id: int
    class_id: int
    name: str

    class Config:
        from_attributes = True


@router.get("", response_model=List[SectionOut])
def list_sections(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return (
        db.query(Section)
        .filter(Section.school_id == current_user["school_id"])
        .order_by(Section.id.asc())
        .all()
    )


@router.post("", response_model=SectionOut, status_code=201)
def create_section(
    payload: SectionCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    # Ensure the class exists and belongs to the same school (tenant isolation)
    cls = (
        db.query(Class)
        .filter(
            Class.id == payload.class_id,
            Class.school_id == current_user["school_id"],
        )
        .first()
    )
    if not cls:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invalid_class_id",
        )

    row = Section(
        school_id=current_user["school_id"],
        class_id=payload.class_id,
        name=payload.name,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
