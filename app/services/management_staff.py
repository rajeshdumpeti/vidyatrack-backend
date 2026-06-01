from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.api.v1.schemas.management_staff import (
    ManagementStaffCompensationUpdateIn,
    ManagementStaffListItem,
    ManagementStaffListOut,
    ManagementStaffPayrollProcessOut,
    ManagementStaffStatsOut,
)
from app.db.models.audit_log import AuditLog
from app.db.models.principal import Principal
from app.db.models.school import School
from app.db.models.staff_compensation_profile import StaffCompensationProfile
from app.db.models.staff_payroll_record import StaffPayrollRecord
from app.db.models.teacher import Teacher
from app.db.models.user import User
from app.db.models.user_school import UserSchool


def _resolve_management_school_id(db: Session, current_user: User, school_id: int | None) -> int:
    rows = (
        db.query(UserSchool)
        .filter(UserSchool.user_id == current_user.id, UserSchool.is_active.is_(True))
        .all()
    )
    if not rows:
        raise HTTPException(status_code=403, detail="missing_school_context")
    if school_id is not None:
        if not any(row.school_id == school_id for row in rows):
            raise HTTPException(status_code=403, detail="invalid_school_context")
        return school_id
    management_link = next((row for row in rows if str(row.role).upper() == "MANAGEMENT"), None)
    return int(management_link.school_id if management_link else rows[0].school_id)


def _month_start(value: date | None) -> date:
    base = value or datetime.now(timezone.utc).date()
    return base.replace(day=1)


def _build_staff_rows(db: Session, school_id: int, month: date) -> list[ManagementStaffListItem]:
    school = db.query(School).filter(School.id == school_id).first()
    school_name = school.name if school else "School"
    compensation_by_user = {
        row.user_id: row
        for row in db.query(StaffCompensationProfile).filter(StaffCompensationProfile.school_id == school_id).all()
    }
    payroll_by_user = {
        row.user_id: row
        for row in db.query(StaffPayrollRecord).filter(
            StaffPayrollRecord.school_id == school_id,
            StaffPayrollRecord.payroll_month == month,
        ).all()
    }

    items: list[ManagementStaffListItem] = []

    teacher_rows = (
        db.query(Teacher, User)
        .join(User, User.id == Teacher.user_id)
        .filter(Teacher.school_id == school_id)
        .all()
    )
    for teacher, user in teacher_rows:
        compensation = compensation_by_user.get(user.id)
        payroll = payroll_by_user.get(user.id)
        items.append(
            ManagementStaffListItem(
                user_id=user.id,
                role="TEACHER",
                name=teacher.name or user.full_name or user.phone,
                employee_id=teacher.public_id,
                school_name=school_name,
                join_date=compensation.date_of_joining if compensation else None,
                monthly_salary=float(compensation.gross_salary) if compensation else 0.0,
                employment_type=compensation.employment_type if compensation else None,
                payment_mode=compensation.payment_mode if compensation else None,
                payroll_status="PAID" if payroll else "PENDING",
                contract_end_date=compensation.contract_end_date if compensation else None,
            )
        )

    principal = db.query(Principal, User).join(User, User.id == Principal.user_id).filter(Principal.school_id == school_id).first()
    if principal:
        principal_row, user = principal
        compensation = compensation_by_user.get(user.id)
        payroll = payroll_by_user.get(user.id)
        items.append(
            ManagementStaffListItem(
                user_id=user.id,
                role="PRINCIPAL",
                name=principal_row.name or user.full_name or user.phone,
                employee_id=principal_row.public_id,
                school_name=school_name,
                join_date=compensation.date_of_joining if compensation else None,
                monthly_salary=float(compensation.gross_salary) if compensation else 0.0,
                employment_type=compensation.employment_type if compensation else None,
                payment_mode=compensation.payment_mode if compensation else None,
                payroll_status="PAID" if payroll else "PENDING",
                contract_end_date=compensation.contract_end_date if compensation else None,
            )
        )
    return sorted(items, key=lambda item: (item.role, item.name.lower()))


def list_staff(
    *,
    db: Session,
    current_user: User,
    school_id: int | None = None,
    search: str | None = None,
    role: str | None = None,
) -> ManagementStaffListOut:
    resolved_school_id = _resolve_management_school_id(db, current_user, school_id)
    items = _build_staff_rows(db, resolved_school_id, _month_start(None))
    if role and role.lower() != "all":
        items = [item for item in items if item.role.lower() == role.lower()]
    if search:
        token = search.lower().strip()
        items = [
            item for item in items
            if token in item.name.lower() or token in item.employee_id.lower()
        ]
    return ManagementStaffListOut(items=items, total=len(items))


def get_staff_stats(*, db: Session, current_user: User, school_id: int | None = None) -> ManagementStaffStatsOut:
    resolved_school_id = _resolve_management_school_id(db, current_user, school_id)
    month = _month_start(None)
    items = _build_staff_rows(db, resolved_school_id, month)
    active_items = [item for item in items if item.role in {"TEACHER", "PRINCIPAL"}]
    monthly_payroll = round(sum(item.monthly_salary for item in active_items), 2)
    pending_payouts = sum(1 for item in active_items if item.payroll_status != "PAID" and item.monthly_salary > 0)
    role_counter = Counter("teaching" if item.role == "TEACHER" else "admin" for item in active_items)
    total = max(len(active_items), 1)
    contracts_expiring_soon = sum(
        1
        for item in active_items
        if item.contract_end_date and 0 <= (item.contract_end_date - month).days <= 30
    )
    next_pay_day = max(
        [
            profile.payment_day
            for profile in db.query(StaffCompensationProfile).filter(StaffCompensationProfile.school_id == resolved_school_id).all()
        ] or [1]
    )
    next_pay_date = month.replace(day=min(max(next_pay_day, 1), 28))
    return ManagementStaffStatsOut(
        monthly_payroll=monthly_payroll,
        active_staff=len(active_items),
        pending_payouts=pending_payouts,
        next_pay_date=next_pay_date,
        composition={
            "teaching_pct": round((role_counter.get("teaching", 0) / total) * 100, 2),
            "admin_pct": round((role_counter.get("admin", 0) / total) * 100, 2),
            "support_pct": 0.0,
        },
        contracts_expiring_soon=contracts_expiring_soon,
    )


def update_staff_compensation(
    *,
    db: Session,
    current_user: User,
    user_id: int,
    payload: ManagementStaffCompensationUpdateIn,
    school_id: int | None = None,
) -> ManagementStaffListItem:
    resolved_school_id = _resolve_management_school_id(db, current_user, school_id)
    link = db.query(UserSchool).filter(
        UserSchool.school_id == resolved_school_id,
        UserSchool.user_id == user_id,
        UserSchool.is_active.is_(True),
    ).first()
    if not link:
        raise HTTPException(status_code=404, detail="staff_not_found")
    role = str(link.role).upper()
    profile = db.query(StaffCompensationProfile).filter(
        StaffCompensationProfile.school_id == resolved_school_id,
        StaffCompensationProfile.user_id == user_id,
    ).first()
    if not profile:
        profile = StaffCompensationProfile(
            school_id=resolved_school_id,
            user_id=user_id,
            role=role,
        )
        db.add(profile)
    profile.gross_salary = payload.gross_salary
    profile.employment_type = payload.employment_type
    profile.payment_mode = payload.payment_mode
    profile.payment_day = payload.payment_day
    profile.date_of_joining = payload.date_of_joining
    profile.contract_end_date = payload.contract_end_date
    db.add(AuditLog(user_id=current_user.id, event="management_staff_compensation_updated", identifier=str(user_id)))
    db.commit()
    items = _build_staff_rows(db, resolved_school_id, _month_start(None))
    match = next((item for item in items if item.user_id == user_id), None)
    if not match:
        raise HTTPException(status_code=404, detail="staff_not_found")
    return match


def process_staff_payroll(
    *,
    db: Session,
    current_user: User,
    school_id: int | None = None,
    user_id: int | None = None,
    payroll_month: date | None = None,
    reference_note: str | None = None,
) -> ManagementStaffPayrollProcessOut:
    resolved_school_id = _resolve_management_school_id(db, current_user, school_id)
    month = _month_start(payroll_month)
    items = _build_staff_rows(db, resolved_school_id, month)
    targets = [item for item in items if (user_id is None or item.user_id == user_id)]
    targets = [item for item in targets if item.monthly_salary > 0 and item.payroll_status != "PAID"]
    for item in targets:
        profile = db.query(StaffCompensationProfile).filter(
            StaffCompensationProfile.school_id == resolved_school_id,
            StaffCompensationProfile.user_id == item.user_id,
        ).first()
        if not profile:
            continue
        db.add(
            StaffPayrollRecord(
                school_id=resolved_school_id,
                user_id=item.user_id,
                payroll_month=month,
                amount=profile.gross_salary,
                payment_mode=profile.payment_mode,
                reference_note=reference_note,
                processed_by_user_id=current_user.id,
            )
        )
    if targets:
        db.add(AuditLog(user_id=current_user.id, event="management_staff_payroll_processed", identifier=str(resolved_school_id)))
    db.commit()
    now = datetime.now(timezone.utc)
    return ManagementStaffPayrollProcessOut(
        success=True,
        processed_count=len(targets),
        payroll_month=month,
        processed_at=now,
    )
