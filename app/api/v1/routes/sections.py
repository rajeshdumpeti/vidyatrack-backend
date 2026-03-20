from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.v1.controllers import sections as sections_controller
from app.api.v1.deps import get_db, get_current_user
from app.api.v1.schemas.sections import SectionCreate, SectionOut
from app.db.models.user import User

router = APIRouter(prefix="/sections", tags=["sections"])


@router.get("", response_model=List[SectionOut])
def list_sections(
    school_id: int = Query(...),
    class_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[SectionOut]:
    return sections_controller.list_sections(
        db=db,
        school_id=school_id,
        class_id=class_id,
    )


@router.post("", response_model=SectionOut, status_code=201)
def create_section(
    payload: SectionCreate,
    school_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> object:
    return sections_controller.create_section(
        db=db,
        school_id=school_id,
        payload=payload,
    )
