from __future__ import annotations

from collections import defaultdict
from datetime import date

from fastapi import HTTPException
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.api.v1.schemas.management_schools import (
    ManagementSchoolOverviewItemOut,
    ManagementSchoolsOverviewDataOut,
    ManagementSchoolsOverviewOut,
    ManagementSchoolsSummaryOut,
)
from app.core.roles import normalize_role
from app.db.models.attendance_record import AttendanceRecord
from app.db.models.audit_log import AuditLog
from app.db.models.class_ import Class
from app.db.models.class_subject import ClassSubject
from app.db.models.fee_payment import FeePayment
from app.db.models.fee_structure import FeeStructure
from app.db.models.fee_structure_item import FeeStructureItem
from app.db.models.principal import Principal
from app.db.models.school import School
from app.db.models.school_academic_details import SchoolAcademicDetails
from app.db.models.school_contact import SchoolContact
from app.db.models.school_features import SchoolFeatures
from app.db.models.section import Section
from app.db.models.student import Student
from app.db.models.teacher import Teacher
from app.db.models.user_school import UserSchool
from app.db.models.user import User
from app.db.repositories import dashboard as dashboard_repository


def _resolve_management_school_ids(*, db: Session, current_user: User) -> list[int]:
    links = dashboard_repository.list_user_school_links(db, user_id=current_user.id)
    school_ids = sorted(
        {
            link.school_id
            for link in links
            if link.is_active and normalize_role(link.role) == "MANAGEMENT"
        }
    )
    if not school_ids:
        raise HTTPException(status_code=403, detail="missing_school_context")
    return school_ids


def _sum_fee_targets(db: Session, *, school_ids: list[int]) -> dict[int, float]:
    rows = (
        db.query(
            FeeStructure.school_id.label("school_id"),
            FeeStructure.grade_name.label("grade_name"),
            func.coalesce(func.sum(FeeStructureItem.amount), 0).label("amount"),
        )
        .join(FeeStructureItem, FeeStructureItem.fee_structure_id == FeeStructure.id)
        .filter(FeeStructure.school_id.in_(school_ids), FeeStructure.is_active.is_(True))
        .group_by(FeeStructure.school_id, FeeStructure.grade_name)
        .all()
    )
    amount_by_grade = {
        (int(row.school_id), str(row.grade_name)): float(row.amount or 0)
        for row in rows
    }

    student_rows = (
        db.query(
            Student.school_id.label("school_id"),
            Class.name.label("class_name"),
            func.count(Student.id).label("student_count"),
        )
        .join(Section, Section.id == Student.section_id, isouter=True)
        .join(Class, Class.id == Section.class_id, isouter=True)
        .filter(Student.school_id.in_(school_ids))
        .group_by(Student.school_id, Class.name)
        .all()
    )

    targets: dict[int, float] = defaultdict(float)
    for row in student_rows:
        class_name = (row.class_name or "").strip()
        if not class_name:
            continue
        grade_name = f"Grade {class_name}" if class_name.isdigit() else class_name
        targets[int(row.school_id)] += amount_by_grade.get(
            (int(row.school_id), grade_name),
            0.0,
        ) * int(row.student_count or 0)
    return targets


def get_management_schools_overview(
    *,
    db: Session,
    current_user: User,
) -> ManagementSchoolsOverviewOut:
    school_ids = _resolve_management_school_ids(db=db, current_user=current_user)
    today = date.today()
    month_start = today.replace(day=1)

    schools = (
        db.query(School)
        .filter(School.id.in_(school_ids))
        .order_by(School.name.asc())
        .all()
    )
    contacts = {
        row.school_id: row
        for row in db.query(SchoolContact).filter(SchoolContact.school_id.in_(school_ids)).all()
    }
    academics = {
        row.school_id: row
        for row in db.query(SchoolAcademicDetails).filter(SchoolAcademicDetails.school_id.in_(school_ids)).all()
    }
    features = {
        row.school_id: row
        for row in db.query(SchoolFeatures).filter(SchoolFeatures.school_id.in_(school_ids)).all()
    }
    principals = {
        row.school_id: row.name
        for row in db.query(Principal).filter(Principal.school_id.in_(school_ids)).all()
    }

    student_counts = dict(
        db.query(Student.school_id, func.count(Student.id))
        .filter(Student.school_id.in_(school_ids))
        .group_by(Student.school_id)
        .all()
    )
    teacher_counts = dict(
        db.query(Teacher.school_id, func.count(Teacher.id))
        .filter(Teacher.school_id.in_(school_ids))
        .group_by(Teacher.school_id)
        .all()
    )
    staff_counts = dict(
        db.query(UserSchool.school_id, func.count(UserSchool.id))
        .filter(
            UserSchool.school_id.in_(school_ids),
            UserSchool.is_active.is_(True),
            ~UserSchool.role.ilike("STUDENT"),
        )
        .group_by(UserSchool.school_id)
        .all()
    )
    sections_counts = dict(
        db.query(Section.school_id, func.count(Section.id))
        .filter(
            Section.school_id.in_(school_ids),
            Section.is_active.is_(True),
        )
        .group_by(Section.school_id)
        .all()
    )
    subjects_counts = dict(
        db.query(ClassSubject.school_id, func.count(ClassSubject.id))
        .filter(
            ClassSubject.school_id.in_(school_ids),
            ClassSubject.is_active.is_(True),
        )
        .group_by(ClassSubject.school_id)
        .all()
    )
    fee_plan_counts = dict(
        db.query(FeeStructure.school_id, func.count(FeeStructure.id))
        .filter(
            FeeStructure.school_id.in_(school_ids),
            FeeStructure.is_active.is_(True),
        )
        .group_by(FeeStructure.school_id)
        .all()
    )
    monthly_collection = dict(
        db.query(FeePayment.school_id, func.coalesce(func.sum(FeePayment.amount_paid), 0))
        .filter(
            FeePayment.school_id.in_(school_ids),
            FeePayment.payment_date >= month_start,
        )
        .group_by(FeePayment.school_id)
        .all()
    )
    total_collection = dict(
        db.query(FeePayment.school_id, func.coalesce(func.sum(FeePayment.amount_paid), 0))
        .filter(FeePayment.school_id.in_(school_ids))
        .group_by(FeePayment.school_id)
        .all()
    )
    annual_targets = _sum_fee_targets(db, school_ids=school_ids)

    attendance_rows = (
        db.query(
            AttendanceRecord.school_id.label("school_id"),
            func.sum(case((AttendanceRecord.status == "present", 1), else_=0)).label("present_count"),
            func.count(AttendanceRecord.id).label("total_count"),
        )
        .filter(
            AttendanceRecord.school_id.in_(school_ids),
            AttendanceRecord.date == today,
        )
        .group_by(AttendanceRecord.school_id)
        .all()
    )
    attendance_pct_by_school: dict[int, float] = {}
    for row in attendance_rows:
        total_count = int(row.total_count or 0)
        present_count = int(row.present_count or 0)
        attendance_pct_by_school[int(row.school_id)] = round((present_count / total_count) * 100, 2) if total_count else 0.0

    user_ids_by_school: dict[int, list[int]] = defaultdict(list)
    for school_id, user_id in (
        db.query(UserSchool.school_id, UserSchool.user_id)
        .filter(
            UserSchool.school_id.in_(school_ids),
            UserSchool.is_active.is_(True),
        )
        .all()
    ):
        user_ids_by_school[int(school_id)].append(int(user_id))

    activity_by_school: dict[int, object] = {}
    for school in schools:
        candidate_dates: list[object] = []
        if user_ids_by_school.get(school.id):
            user_log_at = (
                db.query(func.max(AuditLog.created_at))
                .filter(AuditLog.user_id.in_(user_ids_by_school[school.id]))
                .scalar()
            )
            if user_log_at is not None:
                candidate_dates.append(user_log_at)
        school_log_at = (
            db.query(func.max(AuditLog.created_at))
            .filter(AuditLog.identifier == school.public_id)
            .scalar()
        )
        if school_log_at is not None:
            candidate_dates.append(school_log_at)
        activity_by_school[school.id] = max(candidate_dates) if candidate_dates else None

    items: list[ManagementSchoolOverviewItemOut] = []
    for school in schools:
        contact = contacts.get(school.id)
        academic = academics.get(school.id)
        feature = features.get(school.id)
        steps = [
            bool(contact and any([contact.school_phone, contact.school_email, contact.city, contact.state, contact.pin_code])),
            bool(sections_counts.get(school.id, 0)),
            bool(subjects_counts.get(school.id, 0)),
            bool(fee_plan_counts.get(school.id, 0)),
            bool(principals.get(school.id)),
            bool(teacher_counts.get(school.id, 0)),
            bool(student_counts.get(school.id, 0)),
        ]
        setup_completion_pct = int(round((sum(1 for step in steps if step) / len(steps)) * 100))
        items.append(
            ManagementSchoolOverviewItemOut(
                school_id=school.id,
                school_name=school.name,
                school_code=school.code,
                status=(school.status or "ACTIVE").upper(),
                board=school.board,
                category=school.category,
                current_session=academic.current_session if academic else None,
                city=contact.city if contact else None,
                state=contact.state if contact else None,
                principal_name=principals.get(school.id),
                student_count=int(student_counts.get(school.id, 0) or 0),
                teacher_count=int(teacher_counts.get(school.id, 0) or 0),
                staff_count=int(staff_counts.get(school.id, 0) or 0),
                attendance_pct=attendance_pct_by_school.get(school.id, 0.0),
                fee_collected_mtd=round(float(monthly_collection.get(school.id, 0) or 0), 2),
                fee_pending=round(max(float(annual_targets.get(school.id, 0) or 0) - float(total_collection.get(school.id, 0) or 0), 0.0), 2),
                setup_completion_pct=setup_completion_pct,
                modules_enabled=list(feature.modules_enabled or []) if feature and feature.modules_enabled else [],
                last_activity_at=activity_by_school.get(school.id),
            )
        )

    items.sort(key=lambda item: item.school_name.lower())

    return ManagementSchoolsOverviewOut(
        success=True,
        data=ManagementSchoolsOverviewDataOut(
            summary=ManagementSchoolsSummaryOut(
                total_schools=len(items),
                total_students=sum(item.student_count for item in items),
                total_staff=sum(item.staff_count for item in items),
                monthly_collection=round(sum(item.fee_collected_mtd for item in items), 2),
                pending_collection=round(sum(item.fee_pending for item in items), 2),
            ),
            schools=items,
        ),
    )
