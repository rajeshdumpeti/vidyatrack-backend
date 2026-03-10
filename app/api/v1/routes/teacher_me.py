from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v1.controllers import teacher_me as teacher_me_controller
from app.api.v1.deps import get_db, require_teacher
from app.api.v1.schemas.teacher_me import TeacherAttendanceSectionOut
from app.db.models.user import User

router = APIRouter(prefix="/teachers/me", tags=["teachers-me"])


@router.get("/attendance-section", response_model=TeacherAttendanceSectionOut)
def get_attendance_section(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher),
) -> TeacherAttendanceSectionOut:
    return teacher_me_controller.get_attendance_section(
        db=db,
        current_user=current_user,
    )
