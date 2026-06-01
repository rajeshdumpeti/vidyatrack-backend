from __future__ import annotations

import csv
import io
from datetime import date

from fastapi import HTTPException
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.api.v1.schemas.management_portfolio import (
    ManagementStaffSummaryOut,
    ManagementStudentsSummaryOut,
)
from app.core.roles import normalize_role
from app.db.models.class_ import Class
from app.db.models.principal import Principal
from app.db.models.section import Section
from app.db.models.student import Student
from app.db.models.teacher import Teacher
from app.db.models.teacher_primary_section import TeacherPrimarySection
from app.db.models.user import User
from app.db.models.user_school import UserSchool


def _ensure_management_access(*, db: Session, school_id: int, current_user: User) -> None:
    mapping = (
        db.query(UserSchool)
        .filter(
            UserSchool.school_id == school_id,
            UserSchool.user_id == current_user.id,
            UserSchool.is_active.is_(True),
        )
        .first()
    )
    if not mapping and normalize_role(current_user.role) != "SUPER_ADMIN":
        raise HTTPException(status_code=403, detail={"code": "NO_SCHOOL_ACCESS"})


def get_students_summary(
    *,
    db: Session,
    school_id: int,
    current_user: User,
) -> ManagementStudentsSummaryOut:
    _ensure_management_access(db=db, school_id=school_id, current_user=current_user)
    month_start = date.today().replace(day=1)

    summary = (
        db.query(
            func.count(Student.id).label("total_students"),
            func.sum(case((func.lower(Student.gender) == "female", 1), else_=0)).label("girls_count"),
            func.sum(case((func.lower(Student.gender) == "male", 1), else_=0)).label("boys_count"),
            func.sum(
                case(
                    (
                        (Student.gender.is_not(None))
                        & (func.lower(Student.gender).notin_(["male", "female"])),
                        1,
                    ),
                    else_=0,
                )
            ).label("other_gender_count"),
            func.count(func.distinct(Student.section_id)).label("sections_covered"),
            func.sum(case((Student.admission_date >= month_start, 1), else_=0)).label("new_admissions_this_month"),
        )
        .filter(Student.school_id == school_id)
        .one()
    )
    classes_covered = (
        db.query(func.count(func.distinct(Section.class_id)))
        .join(Student, Student.section_id == Section.id)
        .filter(Student.school_id == school_id)
        .scalar()
        or 0
    )
    return ManagementStudentsSummaryOut(
        total_students=int(summary.total_students or 0),
        girls_count=int(summary.girls_count or 0),
        boys_count=int(summary.boys_count or 0),
        other_gender_count=int(summary.other_gender_count or 0),
        sections_covered=int(summary.sections_covered or 0),
        classes_covered=int(classes_covered or 0),
        new_admissions_this_month=int(summary.new_admissions_this_month or 0),
    )


def get_staff_summary(
    *,
    db: Session,
    school_id: int,
    current_user: User,
) -> ManagementStaffSummaryOut:
    _ensure_management_access(db=db, school_id=school_id, current_user=current_user)
    summary = (
        db.query(
            func.count(Teacher.id).label("total_teachers"),
            func.sum(case((Teacher.status == "ACTIVE", 1), else_=0)).label("active_teachers"),
            func.sum(case((Teacher.status == "ON_LEAVE", 1), else_=0)).label("on_leave_teachers"),
            func.sum(case((Teacher.status.in_(["RESIGNED", "TRANSFERRED"]), 1), else_=0)).label("inactive_teachers"),
        )
        .filter(Teacher.school_id == school_id)
        .one()
    )
    teachers_with_primary_section = (
        db.query(func.count(func.distinct(TeacherPrimarySection.teacher_id)))
        .filter(TeacherPrimarySection.school_id == school_id)
        .scalar()
        or 0
    )
    principal_assigned = (
        db.query(Principal.id).filter(Principal.school_id == school_id).first() is not None
    )
    return ManagementStaffSummaryOut(
        total_teachers=int(summary.total_teachers or 0),
        active_teachers=int(summary.active_teachers or 0),
        on_leave_teachers=int(summary.on_leave_teachers or 0),
        inactive_teachers=int(summary.inactive_teachers or 0),
        teachers_with_primary_section=int(teachers_with_primary_section or 0),
        principal_assigned=principal_assigned,
    )


def export_students_csv(
    *,
    db: Session,
    school_id: int,
    current_user: User,
) -> str:
    _ensure_management_access(db=db, school_id=school_id, current_user=current_user)
    rows = (
        db.query(Student, Section.name.label("section_name"), Class.name.label("class_name"))
        .outerjoin(Section, Section.id == Student.section_id)
        .outerjoin(Class, Class.id == Section.class_id)
        .filter(Student.school_id == school_id)
        .order_by(Class.name.asc().nulls_last(), Section.name.asc().nulls_last(), Student.name.asc())
        .all()
    )
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["student_code", "student_name", "class", "section", "roll_number", "parent_name", "parent_phone", "gender", "admission_date"])
    for student, section_name, class_name in rows:
        writer.writerow([
            student.public_id,
            student.name,
            class_name or "",
            section_name or "",
            student.roll_number or "",
            student.parent_name or "",
            student.parent_phone or "",
            student.gender or "",
            student.admission_date.isoformat() if student.admission_date else "",
        ])
    return buffer.getvalue()


def export_staff_csv(
    *,
    db: Session,
    school_id: int,
    current_user: User,
) -> str:
    _ensure_management_access(db=db, school_id=school_id, current_user=current_user)
    rows = (
        db.query(
            Teacher,
            User.phone.label("phone"),
            User.email.label("user_email"),
            Section.name.label("section_name"),
            Class.name.label("class_name"),
        )
        .outerjoin(User, User.id == Teacher.user_id)
        .outerjoin(TeacherPrimarySection, TeacherPrimarySection.teacher_id == Teacher.id)
        .outerjoin(Section, Section.id == TeacherPrimarySection.section_id)
        .outerjoin(Class, Class.id == Section.class_id)
        .filter(Teacher.school_id == school_id)
        .order_by(Teacher.name.asc())
        .all()
    )
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["teacher_code", "teacher_name", "phone", "email", "status", "primary_class", "primary_section"])
    for teacher, phone, user_email, section_name, class_name in rows:
        writer.writerow([
            teacher.public_id,
            teacher.name,
            phone or "",
            teacher.email or user_email or "",
            teacher.status or "",
            class_name or "",
            section_name or "",
        ])
    return buffer.getvalue()
