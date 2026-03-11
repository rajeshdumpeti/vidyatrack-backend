from fastapi import HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.v1.schemas.management_teachers import (
    ManagementCreateTeacherIn,
    ManagementCreateTeacherOut,
)
from app.core.phone import phone_candidates
from app.db.models.section import Section
from app.db.models.teacher import Teacher
from app.db.models.teacher_primary_section import TeacherPrimarySection
from app.db.models.user import User
from app.db.models.user_school import UserSchool
from app.services.public_id import get_tenant_code_for_school, next_public_id


def management_create_teacher(
    *,
    payload: ManagementCreateTeacherIn,
    response: Response,
    db: Session,
) -> ManagementCreateTeacherOut:
    school_id = payload.school_id
    section = (
        db.query(Section)
        .filter(Section.school_id == school_id, Section.id == payload.section_id)
        .first()
    )
    if not section:
        raise HTTPException(status_code=400, detail="invalid_section_id")

    existing_user = db.query(User).filter(User.phone.in_(phone_candidates(payload.phone))).first()

    teacher = None
    if existing_user:
        existing_access = (
            db.query(UserSchool)
            .filter(
                UserSchool.user_id == existing_user.id,
                UserSchool.school_id == school_id,
            )
            .first()
        )
        if not existing_access:
            db.add(UserSchool(user_id=existing_user.id, school_id=school_id, role="teacher"))

        teacher = (
            db.query(Teacher)
            .filter(Teacher.school_id == school_id, Teacher.user_id == existing_user.id)
            .first()
        )

        if teacher:
            mapping = (
                db.query(TeacherPrimarySection)
                .filter(
                    TeacherPrimarySection.teacher_id == teacher.id,
                    TeacherPrimarySection.school_id == school_id,
                )
                .first()
            )
            if mapping:
                mapping.section_id = payload.section_id
            else:
                db.add(
                    TeacherPrimarySection(
                        school_id=school_id,
                        teacher_id=teacher.id,
                        section_id=payload.section_id,
                    )
                )

            db.commit()
            response.status_code = status.HTTP_200_OK
            return ManagementCreateTeacherOut(
                user_id=existing_user.id,
                teacher_id=teacher.id,
                teacher_public_id=teacher.public_id,
                name=teacher.name,
                email=existing_user.email,
                phone=existing_user.phone,
                section_id=payload.section_id,
            )

    if not existing_user:
        new_user = User(
            role="TEACHER",
            phone=payload.phone,
            email=payload.email,
            is_active=True,
        )
        db.add(new_user)
        db.flush()
        existing_user = new_user
        db.add(UserSchool(user_id=existing_user.id, school_id=school_id, role="teacher"))

    if not teacher:
        teacher = Teacher(
            school_id=school_id,
            user_id=existing_user.id,
            name=payload.name,
            public_id=next_public_id(
                db,
                tenant_code=get_tenant_code_for_school(db, school_id),
                entity="teacher",
            ),
        )
        db.add(teacher)
        db.flush()

    mapping = TeacherPrimarySection(
        school_id=school_id,
        teacher_id=teacher.id,
        section_id=payload.section_id,
    )
    db.add(mapping)
    db.commit()
    db.refresh(teacher)

    return ManagementCreateTeacherOut(
        user_id=existing_user.id,
        teacher_id=teacher.id,
        teacher_public_id=teacher.public_id,
        name=teacher.name,
        email=existing_user.email,
        phone=existing_user.phone,
        section_id=payload.section_id,
    )
