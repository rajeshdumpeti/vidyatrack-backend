from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.api.v1.deps import get_db, get_current_user
from app.db.models.class_ import Class
from app.db.models.section import Section
from app.db.models.user import User

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
    class_name: Optional[str] = None  # Added to hold the joined class name

    class Config:
        from_attributes = True


@router.get("", response_model=List[SectionOut])
def list_sections(
    school_id: int = Query(...),
    class_id: Optional[int] = Query(None),  # Added optional filter
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Section).filter(Section.school_id == school_id)

    if class_id:
        query = query.filter(Section.class_id == class_id)

    results = (
        query.join(Class, Class.id == Section.class_id)
        .add_columns(Class.name.label("class_name"))
        .order_by(Section.name.asc())
        .all()
    )

    sections = []
    for section, class_name in results:
        # Map the SQLAlchemy object to our Pydantic model with the extra class_name
        s_out = SectionOut.from_orm(section)
        s_out.class_name = class_name
        sections.append(s_out)

    return sections


@router.post("", response_model=SectionOut, status_code=201)
def create_section(
    payload: SectionCreate,
    school_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cls = (
        db.query(Class)
        .filter(
            Class.id == payload.class_id,
            Class.school_id == school_id,
        )
        .first()
    )
    if not cls:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invalid_class_id",
        )

    row = Section(
        name=payload.name,
        class_id=payload.class_id,
        school_id=school_id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
