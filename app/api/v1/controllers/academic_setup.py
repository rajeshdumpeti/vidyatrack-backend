from sqlalchemy.orm import Session

from app.api.v1.schemas.academic_setup import AcademicSetupOut
from app.services import academic_setup as academic_setup_service


def get_academic_setup(*, db: Session, school_id: int) -> AcademicSetupOut:
    return academic_setup_service.get_academic_setup(db=db, school_id=school_id)
