from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.api.v1.schemas.dashboard import (
    ManagementDashboardOut,
    PrincipalDashboardOut,
    PrincipalSummary,
)
from app.db.models.user import User
from app.db.repositories import dashboard as dashboard_repository


def _resolve_school_id(*, db: Session, current_user: User, role_name: str) -> int:
    links = dashboard_repository.list_user_school_links(db, user_id=current_user.id)
    if not links:
        raise HTTPException(status_code=403, detail="missing_school_context")

    target_link = next(
        (link for link in links if str(link.role).upper() == role_name),
        None,
    )
    return target_link.school_id if target_link else links[0].school_id


def get_principal_dashboard(*, db: Session, current_user: User) -> PrincipalDashboardOut:
    school_id = _resolve_school_id(db=db, current_user=current_user, role_name="PRINCIPAL")
    today = datetime.now(timezone.utc).date()

    total_students = dashboard_repository.count_students(db, school_id=school_id)
    total_teachers = dashboard_repository.count_teachers(db, school_id=school_id)
    present_today = dashboard_repository.count_attendance_by_status(
        db,
        school_id=school_id,
        for_date=today,
        attendance_status="present",
    )
    absent_today = dashboard_repository.count_attendance_by_status(
        db,
        school_id=school_id,
        for_date=today,
        attendance_status="absent",
    )
    total_today = present_today + absent_today
    attendance_pct = round((present_today / total_today) * 100, 2) if total_today else 0.0

    return PrincipalDashboardOut(
        total_students=total_students,
        total_teachers=total_teachers,
        attendance_today_pct=attendance_pct,
        attendance_today_present=present_today,
        attendance_today_absent=absent_today,
        attendance_today_total=total_today,
        notices=[],
    )


def get_management_dashboard(*, db: Session, current_user: User) -> ManagementDashboardOut:
    school_id = _resolve_school_id(db=db, current_user=current_user, role_name="MANAGEMENT")
    today = datetime.now(timezone.utc).date()

    total_students = dashboard_repository.count_students(db, school_id=school_id)
    total_teachers = dashboard_repository.count_teachers(db, school_id=school_id)
    present_today = dashboard_repository.count_attendance_by_status(
        db,
        school_id=school_id,
        for_date=today,
        attendance_status="present",
    )
    absent_today = dashboard_repository.count_attendance_by_status(
        db,
        school_id=school_id,
        for_date=today,
        attendance_status="absent",
    )
    total_today = present_today + absent_today
    attendance_pct = round((present_today / total_today) * 100, 2) if total_today else 0.0

    principal = dashboard_repository.get_principal_for_school(db, school_id=school_id)

    return ManagementDashboardOut(
        total_students=total_students,
        total_teachers=total_teachers,
        attendance_today_pct=attendance_pct,
        attendance_today_present=present_today,
        attendance_today_absent=absent_today,
        attendance_today_total=total_today,
        principal=PrincipalSummary(
            assigned=principal is not None,
            principal_id=principal.id if principal else None,
            name=principal.name if principal else None,
        ),
        notices=[],
    )
