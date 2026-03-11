from sqlalchemy.orm import Session

from app.api.v1.schemas.teachers_me import (
    TeacherAttendanceSectionOut,
    TeacherContextOut,
    TeacherMeOut,
    TeacherReadinessOut,
    TeachingAssignmentOut,
)
from app.db.models.user import User
from app.services import teachers_me as teachers_me_service


def get_my_teacher_profile(*, db: Session, current_user: User) -> TeacherMeOut:
    return teachers_me_service.get_my_teacher_profile(db=db, current_user=current_user)


def get_my_teacher_context(*, db: Session, school_id: int, current_user: User) -> TeacherContextOut:
    return teachers_me_service.get_my_teacher_context(
        db=db,
        school_id=school_id,
        current_user=current_user,
    )


def get_my_teaching_assignments(
    *,
    db: Session,
    current_user: User,
) -> list[TeachingAssignmentOut]:
    return teachers_me_service.get_my_teaching_assignments(db=db, current_user=current_user)


def get_my_attendance_section(*, db: Session, current_user: User) -> TeacherAttendanceSectionOut:
    return teachers_me_service.get_my_attendance_section(db=db, current_user=current_user)


def get_my_teacher_readiness(*, db: Session, current_user: User) -> TeacherReadinessOut:
    return teachers_me_service.get_my_teacher_readiness(db=db, current_user=current_user)
