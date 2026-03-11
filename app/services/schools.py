from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.api.v1.schemas.schools import (
    SchoolCreate,
    SchoolDashboardOut,
    SchoolStaffListItem,
    SchoolStudentListItem,
    SchoolTeacherListItem,
)
from app.core.roles import normalize_role
from app.db.models.school import School
from app.db.models.user import User
from app.db.models.user_school import UserSchool
from app.db.repositories import schools as schools_repository
from app.services.public_id import derive_tenant_code, ensure_unique_tenant_code, next_public_id


def _get_school_or_404(db: Session, school_id: int) -> School:
    school = schools_repository.get_school_by_id(db, school_id)
    if not school:
        raise HTTPException(status_code=404, detail="school_not_found")
    return school


def list_schools(*, db: Session) -> list[School]:
    schools = schools_repository.list_schools(db)
    for school in schools:
        school.teacher_count = schools_repository.count_user_school_role(
            db,
            school_id=school.id,
            role="teacher",
        )
        school.student_count = schools_repository.count_user_school_role(
            db,
            school_id=school.id,
            role="student",
        )
    return schools


def get_school_dashboard(*, school_id: int, db: Session) -> SchoolDashboardOut:
    school = _get_school_or_404(db, school_id)
    teacher_count = schools_repository.count_teachers(db, school_id=school_id)
    student_count = schools_repository.count_students(db, school_id=school_id)
    staff_count = schools_repository.count_staff(db, school_id=school_id)
    return SchoolDashboardOut(
        school_id=school_id,
        school_public_id=school.public_id,
        teacher_count=teacher_count,
        student_count=student_count,
        staff_count=staff_count,
        total_registered=teacher_count + student_count + staff_count,
    )


def get_school_teachers(*, school_id: int, db: Session) -> list[SchoolTeacherListItem]:
    _get_school_or_404(db, school_id)
    rows = schools_repository.list_school_teachers(db, school_id=school_id)
    return [
        SchoolTeacherListItem(
            id=teacher.id,
            school_id=teacher.school_id,
            name=teacher.name,
            email=teacher.email or (user.email if user else None),
            phone=(user.phone if user else None),
            status="active" if (not user or user.is_active) else "inactive",
        )
        for teacher, user in rows
    ]


def get_school_students(*, school_id: int, db: Session) -> list[SchoolStudentListItem]:
    _get_school_or_404(db, school_id)
    students = schools_repository.list_school_students(db, school_id=school_id)
    return [
        SchoolStudentListItem(
            id=student.id,
            school_id=student.school_id,
            name=student.name,
            parent_name=student.parent_name,
            parent_phone=student.parent_phone,
            status="active",
        )
        for student in students
    ]


def get_school_staff(*, school_id: int, db: Session) -> list[SchoolStaffListItem]:
    _get_school_or_404(db, school_id)
    rows = schools_repository.list_school_staff(db, school_id=school_id)
    return [
        SchoolStaffListItem(
            user_id=user.id,
            school_id=link.school_id,
            role=link.role,
            name=(user.email or user.phone or f"User {user.id}"),
            email=user.email,
            phone=user.phone,
            status="active" if user.is_active else "inactive",
        )
        for link, user in rows
    ]


def create_school(*, payload: SchoolCreate, db: Session, current_user: User) -> School:
    if normalize_role(current_user.role) != "SUPER_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Super Admins can onboard new schools",
        )
    try:
        tenant_code = ensure_unique_tenant_code(db, derive_tenant_code(payload.name))
        new_school = School(
            name=payload.name,
            code=tenant_code,
            public_id=next_public_id(
                db,
                tenant_code=tenant_code,
                entity="school",
            ),
        )
        db.add(new_school)
        db.flush()

        existing_user = schools_repository.get_user_by_phone(
            db,
            phone=payload.admin_phone,
        )
        if not existing_user:
            admin_user = User(
                phone=payload.admin_phone,
                email=payload.admin_email,
                role="management",
                is_active=True,
            )
            db.add(admin_user)
            db.flush()
        else:
            admin_user = existing_user
            if payload.admin_email and not admin_user.email:
                admin_user.email = payload.admin_email
                db.add(admin_user)

        mapping = UserSchool(
            user_id=admin_user.id,
            school_id=new_school.id,
            role="management",
        )
        db.add(mapping)

        db.commit()
        db.refresh(new_school)
        return new_school
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to onboard school: {str(exc)}",
        )
