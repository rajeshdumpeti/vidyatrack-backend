from sqlalchemy.orm import Session

from app.api.v1.schemas.teacher_me import TeacherAttendanceSectionOut
from app.db.models.user import User
from app.services.teacher_me import get_attendance_section as get_attendance_section_service


def get_attendance_section(*, db: Session, current_user: User) -> TeacherAttendanceSectionOut:
    return get_attendance_section_service(db=db, current_user=current_user)
