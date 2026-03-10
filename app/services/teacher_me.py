from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.api.v1.schemas.teacher_me import TeacherAttendanceSectionOut
from app.db.models.user import User
from app.db.repositories import teacher_me as teacher_me_repository


def get_attendance_section(*, db: Session, current_user: User) -> TeacherAttendanceSectionOut:
    teacher = teacher_me_repository.get_teacher_by_user_id(db, user_id=current_user.id)
    if not teacher:
        raise HTTPException(status_code=404, detail="teacher_not_found")

    school_id = teacher.school_id
    mapping = teacher_me_repository.get_primary_section_mapping(
        db,
        school_id=school_id,
        teacher_id=teacher.id,
    )
    if not mapping:
        raise HTTPException(status_code=404, detail="no_primary_section_assigned")

    section = teacher_me_repository.get_section(
        db,
        school_id=school_id,
        section_id=mapping.section_id,
    )
    if not section:
        raise HTTPException(status_code=400, detail="invalid_section_id")

    class_ = teacher_me_repository.get_class_for_section(
        db,
        school_id=school_id,
        class_id=section.class_id,
    )
    if not class_:
        raise HTTPException(status_code=400, detail="invalid_class_id")

    return TeacherAttendanceSectionOut(
        section_id=section.id,
        section_name=section.name,
        class_id=class_.id,
        class_name=class_.name,
    )
