from __future__ import annotations

import math

from sqlalchemy.orm import Session

from app.api.v1.schemas.schools import PaginatedResponse
from app.api.v1.schemas.teachers import TeacherCreate, TeacherOut
from app.core.phone import normalize_phone
from app.db.models.teacher import Teacher
from app.db.models.teacher_primary_section import TeacherPrimarySection
from app.db.models.user import User
from app.db.models.user_school import UserSchool
from app.db.repositories import teachers as teachers_repository
from app.services.public_id import get_tenant_code_for_school, next_public_id


def _build_teacher_outs(
    teachers: list[Teacher],
    *,
    db: Session,
    school_id: int,
) -> list[TeacherOut]:
    teacher_ids = [teacher.id for teacher in teachers]
    user_ids = [teacher.user_id for teacher in teachers if teacher.user_id]

    users_by_id = {
        user.id: user
        for user in teachers_repository.list_users_by_ids(db, user_ids=user_ids)
    }

    primary_section_rows = teachers_repository.list_primary_sections(
        db,
        school_id=school_id,
        teacher_ids=teacher_ids,
    )
    assigned_section_by_teacher = {
        row.teacher_id: f"{row.class_name} - {row.section_name}"
        for row in primary_section_rows
    }

    assignment_rows = teachers_repository.list_assignment_rows(
        db,
        school_id=school_id,
        teacher_ids=teacher_ids,
    )
    assignments_by_teacher: dict[int, list[dict]] = {}
    for row in assignment_rows:
        assignments_by_teacher.setdefault(row.teacher_id, []).append(
            {"label": f"{row.subject_name} • {row.class_name}-{row.section_name}"}
        )

    return [
        TeacherOut(
            id=teacher.id,
            public_id=teacher.public_id,
            school_id=teacher.school_id,
            user_id=teacher.user_id,
            name=teacher.name,
            email=teacher.email
            or (users_by_id[teacher.user_id].email if teacher.user_id in users_by_id else None),
            phone=users_by_id.get(teacher.user_id).phone if teacher.user_id in users_by_id else None,
            employee_id=teacher.public_id,
            status="active"
            if (teacher.user_id not in users_by_id or users_by_id[teacher.user_id].is_active)
            else "inactive",
            assigned_section_label=assigned_section_by_teacher.get(teacher.id),
            assignments=assignments_by_teacher.get(teacher.id, []),
        )
        for teacher in teachers
    ]


def list_teachers(*, db: Session, school_id: int) -> list[TeacherOut]:
    teachers = teachers_repository.list_teachers_for_school(db, school_id=school_id)
    return _build_teacher_outs(teachers, db=db, school_id=school_id)


def list_teachers_paginated(
    *,
    db: Session,
    school_id: int,
    search: str | None = None,
    page: int = 1,
    limit: int = 25,
) -> PaginatedResponse[TeacherOut]:
    teachers, total = teachers_repository.list_teachers_paginated(
        db,
        school_id=school_id,
        search=search,
        page=page,
        limit=limit,
    )
    items = _build_teacher_outs(teachers, db=db, school_id=school_id)
    return PaginatedResponse(
        data=items,
        total=total,
        page=page,
        limit=limit,
        total_pages=math.ceil(total / limit) if limit else 1,
    )


def create_teacher(*, db: Session, payload: TeacherCreate) -> Teacher:
    school_id = payload.school_id
    normalized_phone = normalize_phone(payload.phone)

    user = teachers_repository.get_user_by_phone(db, normalized_phone=normalized_phone)
    if not user:
        user = User(
            role="TEACHER",
            phone=normalized_phone,
            email=payload.email,
            is_active=True,
        )
        db.add(user)
        db.flush()
    elif payload.email is not None and payload.email.strip():
        if user.email != payload.email.strip():
            user.email = payload.email.strip()
            db.add(user)

    teacher = teachers_repository.get_teacher_by_school_and_user(
        db,
        school_id=school_id,
        user_id=user.id,
    )
    if not teacher:
        teacher = Teacher(
            school_id=school_id,
            user_id=user.id,
            name=payload.name,
            email=payload.email,
            public_id=next_public_id(
                db,
                tenant_code=get_tenant_code_for_school(db, school_id),
                entity="teacher",
            ),
        )
        db.add(teacher)
        db.flush()

    user_school = teachers_repository.get_user_school_link(
        db,
        user_id=user.id,
        school_id=school_id,
    )
    if not user_school:
        db.add(UserSchool(user_id=user.id, school_id=school_id, role="teacher"))

    if payload.section_id:
        db.merge(
            TeacherPrimarySection(
                school_id=school_id,
                teacher_id=teacher.id,
                section_id=payload.section_id,
            )
        )

    db.commit()
    db.refresh(teacher)
    return teacher
