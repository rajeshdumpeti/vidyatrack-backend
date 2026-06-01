from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
import uuid

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.v1.schemas.dashboard import (
    DashboardNotice,
    ManagementDashboardAlertActionOut,
    ManagementDashboardAlertHistoryItem,
    ManagementDashboardAlertHistoryOut,
    ManagementDashboardActivityItem,
    ManagementDashboardAlert,
    ManagementDashboardData,
    ManagementDashboardFeeChartItem,
    ManagementDashboardKpis,
    ManagementDashboardOut,
    ManagementDashboardQuarterlyOutlook,
    ManagementDashboardSchoolMatrixRow,
    ManagementDashboardSchoolOption,
    PrincipalDashboardOut,
    PrincipalSummary,
)
from app.core.roles import normalize_role
from app.db.models.attendance_record import AttendanceRecord
from app.db.models.audit_log import AuditLog
from app.db.models.class_ import Class
from app.db.models.fee_payment import FeePayment
from app.db.models.fee_structure import FeeStructure
from app.db.models.fee_structure_item import FeeStructureItem
from app.db.models.principal import Principal
from app.db.models.school import School
from app.db.models.section import Section
from app.db.models.student import Student
from app.db.models.teacher import Teacher
from app.db.models.user import User
from app.db.models.user_school import UserSchool
from app.db.repositories import dashboard as dashboard_repository
from app.integrations.email.brevo import send_management_alert_email
from app.integrations.whatsapp.client import send_management_alert_sms


MONTH_LABELS = ["Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "Jan", "Feb", "Mar"]


def _resolve_school_ids(*, db: Session, current_user: User, role_name: str, school_id: int | None) -> tuple[list[int], int | None]:
    links = dashboard_repository.list_user_school_links(db, user_id=current_user.id)
    if not links:
        raise HTTPException(status_code=403, detail="missing_school_context")

    allowed_ids = sorted(
        {
            link.school_id
            for link in links
            if normalize_role(link.role) == role_name and link.is_active
        }
    )
    if not allowed_ids:
        allowed_ids = sorted({link.school_id for link in links if link.is_active})
    if school_id is not None:
        if school_id not in allowed_ids:
            raise HTTPException(status_code=403, detail="missing_school_context")
        return [school_id], school_id
    return allowed_ids, None


def _sum_fee_targets(db: Session, *, school_ids: list[int]) -> tuple[float, dict[int, float]]:
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
    amount_by_grade: dict[tuple[int, str], float] = {
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

    school_targets: dict[int, float] = defaultdict(float)
    for row in student_rows:
        class_name = (row.class_name or "").strip()
        if not class_name:
            continue
        grade_name = f"Grade {class_name}" if class_name.isdigit() else class_name
        school_targets[int(row.school_id)] += amount_by_grade.get((int(row.school_id), grade_name), 0.0) * int(row.student_count or 0)

    total = sum(school_targets.values())
    return total, school_targets


def _monthly_actuals(db: Session, *, school_ids: list[int], academic_year: str | None) -> dict[str, float]:
    query = db.query(FeePayment).filter(FeePayment.school_id.in_(school_ids))
    if academic_year:
        query = query.filter(FeePayment.session == academic_year)
    rows = query.all()
    by_month: dict[str, float] = {month: 0.0 for month in MONTH_LABELS}
    for row in rows:
        if not row.payment_date:
            continue
        month_idx = row.payment_date.month
        label = MONTH_LABELS[month_idx - 4] if month_idx >= 4 else MONTH_LABELS[month_idx + 8]
        by_month[label] += float(row.amount_paid or 0)
    return by_month


def _build_alerts(*, selected_school_id: int | None, fee_pending: float, attendance_pct: float, principal: Principal | None, today: datetime) -> list[ManagementDashboardAlert]:
    alerts: list[ManagementDashboardAlert] = []
    if fee_pending > 0:
        alerts.append(
            ManagementDashboardAlert(
                id=str(uuid.uuid4()),
                type="fee_overdue",
                severity="critical",
                title="Pending fee collection requires attention",
                description="Outstanding fees remain unpaid for the current configured fee plans.",
                count=1,
                school_id=selected_school_id,
                action_type="view_list",
                created_at=today,
            )
        )
    if attendance_pct and attendance_pct < 85:
        alerts.append(
            ManagementDashboardAlert(
                id=str(uuid.uuid4()),
                type="attendance_drop",
                severity="warning",
                title="Attendance dropped below target",
                description="Average attendance is below 85% and principal follow-up is required.",
                count=1,
                school_id=selected_school_id,
                action_type="notify_principal",
                created_at=today,
            )
        )
    if principal is None:
        alerts.append(
            ManagementDashboardAlert(
                id=str(uuid.uuid4()),
                type="principal_missing",
                severity="info",
                title="Principal assignment pending",
                description="Assign a principal before handing over daily school operations.",
                count=1,
                school_id=selected_school_id,
                action_type="open_schedule",
                created_at=today,
            )
        )
    return alerts


def _load_recent_activity(db: Session, *, school_ids: list[int]) -> list[ManagementDashboardActivityItem]:
    mapped_user_ids = (
        db.execute(
            select(UserSchool.user_id).where(
                UserSchool.school_id.in_(school_ids),
                UserSchool.is_active.is_(True),
            )
        )
        .scalars()
        .all()
    )
    school_public_ids = (
        db.execute(select(School.public_id).where(School.id.in_(school_ids))).scalars().all()
    )
    rows = (
        db.query(AuditLog, User)
        .outerjoin(User, User.id == AuditLog.user_id)
        .filter(
            (AuditLog.user_id.in_(mapped_user_ids) if mapped_user_ids else False)
            | (AuditLog.identifier.in_(school_public_ids) if school_public_ids else False)
        )
        .order_by(AuditLog.created_at.desc())
        .limit(10)
        .all()
    )
    label_map = {
        "SCHOOL_ONBOARDED": "School onboarded",
        "SCHOOL_EDITED": "School details updated",
        "SCHOOL_MODULES_UPDATED": "Modules updated",
        "fee_structure_created": "Fee plan created",
        "login_success": "Logged in",
        "password_reset_complete": "Password reset completed",
    }
    items: list[ManagementDashboardActivityItem] = []
    for log, user in rows:
        items.append(
            ManagementDashboardActivityItem(
                event_type=log.event,
                description=label_map.get(log.event, (log.event or "").replace("_", " ").title()),
                performed_by=(user.full_name if user and user.full_name else user.email if user and user.email else log.identifier or "Unknown"),
                performed_at=log.created_at,
            )
        )
    return items


def get_principal_dashboard(*, db: Session, current_user: User) -> PrincipalDashboardOut:
    school_ids, selected_school_id = _resolve_school_ids(
        db=db, current_user=current_user, role_name="PRINCIPAL", school_id=None
    )
    school_id = selected_school_id or school_ids[0]
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


def get_management_dashboard(
    *,
    db: Session,
    current_user: User,
    school_id: int | None = None,
    academic_year: str | None = None,
) -> ManagementDashboardOut:
    school_ids, selected_school_id = _resolve_school_ids(
        db=db, current_user=current_user, role_name="MANAGEMENT", school_id=school_id
    )
    today = datetime.now(timezone.utc)
    today_date = today.date()
    month_start = today_date.replace(day=1)
    previous_month_start = (month_start - timedelta(days=1)).replace(day=1)

    selector_rows = db.query(School).filter(School.id.in_(school_ids)).order_by(School.name.asc()).all()
    school_selector = [
        ManagementDashboardSchoolOption(
            id=row.id,
            name=row.name,
            is_selected=(selected_school_id == row.id) if selected_school_id is not None else (idx == 0),
        )
        for idx, row in enumerate(selector_rows)
    ]

    total_students = (
        db.query(func.count(Student.id)).filter(Student.school_id.in_(school_ids)).scalar() or 0
    )
    current_month_enrollments = (
        db.query(func.count(Student.id))
        .filter(Student.school_id.in_(school_ids), Student.admission_date >= month_start)
        .scalar()
        or 0
    )
    previous_month_enrollments = (
        db.query(func.count(Student.id))
        .filter(
            Student.school_id.in_(school_ids),
            Student.admission_date >= previous_month_start,
            Student.admission_date < month_start,
        )
        .scalar()
        or 0
    )
    students_growth_pct = (
        round(((current_month_enrollments - previous_month_enrollments) / previous_month_enrollments) * 100, 2)
        if previous_month_enrollments
        else float(current_month_enrollments * 100 if current_month_enrollments else 0)
    )

    fee_collected_mtd = (
        db.query(func.coalesce(func.sum(FeePayment.amount_paid), 0))
        .filter(
            FeePayment.school_id.in_(school_ids),
            FeePayment.payment_date >= month_start,
        )
        .scalar()
        or 0
    )
    total_target_annual, school_targets = _sum_fee_targets(db, school_ids=school_ids)
    monthly_target = total_target_annual / 12 if total_target_annual else 0.0
    total_paid_session = (
        db.query(func.coalesce(func.sum(FeePayment.amount_paid), 0))
        .filter(FeePayment.school_id.in_(school_ids))
        .scalar()
        or 0
    )
    fee_pending = max(total_target_annual - float(total_paid_session), 0.0)
    fee_target_pct = round((float(fee_collected_mtd) / monthly_target) * 100, 2) if monthly_target else 0.0
    fee_overdue_days = 14 if fee_pending > 0 else 0

    total_staff = (
        db.query(func.count(UserSchool.id))
        .filter(
            UserSchool.school_id.in_(school_ids),
            UserSchool.is_active.is_(True),
            ~UserSchool.role.ilike("STUDENT"),
        )
        .scalar()
        or 0
    )
    new_joiners_this_month = (
        db.query(func.count(Teacher.id))
        .filter(Teacher.school_id.in_(school_ids))
        .scalar()
        or 0
    )

    present_today = (
        db.query(func.count(AttendanceRecord.id))
        .filter(
            AttendanceRecord.school_id.in_(school_ids),
            AttendanceRecord.date == today_date,
            AttendanceRecord.status == "present",
        )
        .scalar()
        or 0
    )
    absent_today = (
        db.query(func.count(AttendanceRecord.id))
        .filter(
            AttendanceRecord.school_id.in_(school_ids),
            AttendanceRecord.date == today_date,
            AttendanceRecord.status == "absent",
        )
        .scalar()
        or 0
    )
    total_today = present_today + absent_today
    avg_attendance_pct = round((present_today / total_today) * 100, 2) if total_today else 0.0
    previous_day = today_date - timedelta(days=1)
    previous_present = (
        db.query(func.count(AttendanceRecord.id))
        .filter(
            AttendanceRecord.school_id.in_(school_ids),
            AttendanceRecord.date == previous_day,
            AttendanceRecord.status == "present",
        )
        .scalar()
        or 0
    )
    previous_absent = (
        db.query(func.count(AttendanceRecord.id))
        .filter(
            AttendanceRecord.school_id.in_(school_ids),
            AttendanceRecord.date == previous_day,
            AttendanceRecord.status == "absent",
        )
        .scalar()
        or 0
    )
    previous_total = previous_present + previous_absent
    previous_pct = round((previous_present / previous_total) * 100, 2) if previous_total else avg_attendance_pct
    if avg_attendance_pct > previous_pct:
        attendance_trend = "improving"
    elif avg_attendance_pct < previous_pct:
        attendance_trend = "declining"
    else:
        attendance_trend = "stable"

    principal_school_id = selected_school_id or (school_ids[0] if school_ids else None)
    principal = (
        db.query(Principal)
        .filter(Principal.school_id == principal_school_id)
        .first()
        if principal_school_id is not None
        else None
    )

    monthly_actuals = _monthly_actuals(db, school_ids=school_ids, academic_year=academic_year)
    fee_chart = [
        ManagementDashboardFeeChartItem(
            month=month,
            actual=round(monthly_actuals.get(month, 0.0), 2),
            target=round(monthly_target, 2),
        )
        for month in MONTH_LABELS
    ]

    matrix_rows: list[ManagementDashboardSchoolMatrixRow] = []
    for school_row in selector_rows:
        enrollment = dashboard_repository.count_students(db, school_id=school_row.id)
        collection = (
            db.query(func.coalesce(func.sum(FeePayment.amount_paid), 0))
            .filter(FeePayment.school_id == school_row.id, FeePayment.payment_date >= month_start)
            .scalar()
            or 0
        )
        school_present = dashboard_repository.count_attendance_by_status(
            db, school_id=school_row.id, for_date=today_date, attendance_status="present"
        )
        school_absent = dashboard_repository.count_attendance_by_status(
            db, school_id=school_row.id, for_date=today_date, attendance_status="absent"
        )
        school_total = school_present + school_absent
        school_attendance_pct = round((school_present / school_total) * 100, 2) if school_total else 0.0
        collection_target = (school_targets.get(school_row.id, 0.0) / 12) if school_targets.get(school_row.id) else 0.0
        collection_pct = (float(collection) / collection_target * 100) if collection_target else 0.0
        score = (school_attendance_pct * 0.4) + (min(collection_pct, 100) * 0.4) + (min(max(students_growth_pct, 0), 100) * 0.2)
        grade = "A+" if score >= 90 else "A" if score >= 80 else "B" if score >= 70 else "C"
        matrix_rows.append(
            ManagementDashboardSchoolMatrixRow(
                school_id=school_row.id,
                school_name=school_row.name,
                enrollment=enrollment,
                collection=float(collection),
                attendance_pct=school_attendance_pct,
                grade=grade,
            )
        )

    projected_revenue = round(float(fee_collected_mtd) * 3, 2)
    previous_quarter_projection = projected_revenue * 0.9 if projected_revenue else 0.0
    growth_forecast_pct = round(((projected_revenue - previous_quarter_projection) / previous_quarter_projection) * 100, 2) if previous_quarter_projection else 0.0
    target_accomplished_pct = round((projected_revenue / (monthly_target * 3)) * 100, 2) if monthly_target else 0.0

    alerts = _build_alerts(
        selected_school_id=principal_school_id,
        fee_pending=fee_pending,
        attendance_pct=avg_attendance_pct,
        principal=principal,
        today=today,
    )
    recent_activity = _load_recent_activity(db, school_ids=school_ids)

    return ManagementDashboardOut(
        success=True,
        data=ManagementDashboardData(
            school_selector=school_selector,
            kpis=ManagementDashboardKpis(
                total_students=int(total_students),
                students_growth_pct=students_growth_pct,
                fee_collected_mtd=round(float(fee_collected_mtd), 2),
                fee_target_pct=fee_target_pct,
                fee_pending=round(fee_pending, 2),
                fee_overdue_days=fee_overdue_days,
                total_staff=int(total_staff),
                new_joiners_this_month=int(new_joiners_this_month),
                avg_attendance_pct=avg_attendance_pct,
                attendance_trend=attendance_trend,
            ),
            fee_chart=fee_chart,
            alerts=alerts,
            school_matrix=matrix_rows,
            quarterly_outlook=ManagementDashboardQuarterlyOutlook(
                projected_revenue=projected_revenue,
                growth_forecast_pct=growth_forecast_pct,
                target_accomplished_pct=target_accomplished_pct,
            ),
            recent_activity=recent_activity,
            principal=PrincipalSummary(
                assigned=principal is not None,
                principal_id=principal.id if principal else None,
                name=principal.name if principal else None,
            ),
        ),
    )


ALERT_ACTION_EVENT_MAP = {
    ("fee_overdue", "view_list"): (
        "management_alert_fee_overdue_viewed",
        "Fee overdue list opened",
        "Management reviewed overdue fee collections.",
    ),
    ("attendance_drop", "notify_principal"): (
        "management_alert_attendance_principal_notified",
        "Principal notified for attendance drop",
        "Management recorded follow-up on low attendance with the principal.",
    ),
    ("principal_missing", "open_schedule"): (
        "management_alert_principal_schedule_opened",
        "Principal assignment follow-up opened",
        "Management opened the principal assignment workflow.",
    ),
}


def log_management_alert_action(
    *,
    db: Session,
    current_user: User,
    alert_type: str,
    action_type: str,
    school_id: int | None = None,
) -> ManagementDashboardAlertActionOut:
    school_ids, selected_school_id = _resolve_school_ids(
        db=db,
        current_user=current_user,
        role_name="MANAGEMENT",
        school_id=school_id,
    )
    effective_school_id = selected_school_id or (school_ids[0] if school_ids else None)
    school = (
        db.query(School).filter(School.id == effective_school_id).first()
        if effective_school_id is not None
        else None
    )
    event_name, title, description = ALERT_ACTION_EVENT_MAP.get(
        (alert_type, action_type),
        (
            f"management_alert_{alert_type}_{action_type}",
            "Alert action logged",
            "Management recorded an alert follow-up action.",
        ),
    )
    message = title

    if alert_type == "attendance_drop" and action_type == "notify_principal":
        principal = (
            db.query(Principal)
            .filter(Principal.school_id == effective_school_id)
            .first()
            if effective_school_id is not None
            else None
        )
        if principal is None:
            raise HTTPException(status_code=409, detail="principal_not_assigned")

        principal_user = db.query(User).filter(User.id == principal.user_id).first()
        if principal_user is None:
            raise HTTPException(status_code=409, detail="principal_user_missing")

        alert_title = "Attendance dropped below target"
        alert_description = "Average attendance is below 85%. Review attendance exceptions and intervene today."
        delivery_channels: list[str] = []
        delivery_failures: list[str] = []

        if principal_user.phone:
            sms_result = send_management_alert_sms(
                principal_user.phone,
                school_name=school.name if school else "your school",
                alert_title=alert_title,
                alert_description=alert_description,
            )
            if sms_result.success:
                delivery_channels.append("WhatsApp")
            else:
                delivery_failures.append(f"WhatsApp: {sms_result.provider_error_message or 'delivery_failed'}")

        if principal_user.email:
            email_result = send_management_alert_email(
                principal_user.email,
                principal_name=principal.name,
                school_name=school.name if school else "your school",
                alert_title=alert_title,
                alert_description=alert_description,
            )
            if email_result.success:
                delivery_channels.append("Email")
            else:
                delivery_failures.append(f"Email: {email_result.provider_error_message or 'delivery_failed'}")

        if delivery_channels:
            title = "Principal notified for attendance drop"
            description = (
                f"Management notified principal {principal.name} via {', '.join(delivery_channels)}."
            )
            message = f"{title} via {', '.join(delivery_channels)}"
        else:
            title = "Principal notification attempted"
            description = (
                f"Management attempted to notify principal {principal.name}, but no delivery channel succeeded."
            )
            failure_message = "; ".join(delivery_failures) if delivery_failures else "No phone or email configured for the principal."
            message = f"{title}. {failure_message}"

    log = AuditLog(
        user_id=current_user.id,
        event=event_name,
        identifier=school.public_id if school else str(effective_school_id or ""),
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return ManagementDashboardAlertActionOut(
        success=True,
        message=message,
        action_logged_at=log.created_at,
    )


def get_management_alert_history(
    *,
    db: Session,
    current_user: User,
    school_id: int | None = None,
) -> ManagementDashboardAlertHistoryOut:
    school_ids, selected_school_id = _resolve_school_ids(
        db=db,
        current_user=current_user,
        role_name="MANAGEMENT",
        school_id=school_id,
    )
    effective_school_ids = [selected_school_id] if selected_school_id is not None else school_ids
    schools = (
        db.query(School.id, School.public_id)
        .filter(School.id.in_(effective_school_ids))
        .all()
    )
    identifiers = [row.public_id for row in schools if row.public_id]
    user_ids = (
        db.execute(
            select(UserSchool.user_id).where(
                UserSchool.school_id.in_(effective_school_ids),
                UserSchool.is_active.is_(True),
            )
        )
        .scalars()
        .all()
    )
    rows = (
        db.query(AuditLog)
        .filter(
            (
                AuditLog.event.like("management_alert_%")
            )
            & (
                (AuditLog.identifier.in_(identifiers) if identifiers else False)
                | (AuditLog.user_id.in_(user_ids) if user_ids else False)
            )
        )
        .order_by(AuditLog.created_at.desc())
        .limit(10)
        .all()
    )
    title_map = {
        "management_alert_fee_overdue_viewed": (
            "Fee overdue list opened",
            "Management reviewed pending fee collections.",
        ),
        "management_alert_attendance_principal_notified": (
            "Principal notified",
            "Management sent an attendance follow-up to the principal.",
        ),
        "management_alert_principal_schedule_opened": (
            "Principal assignment workflow opened",
            "Management opened the principal assignment follow-up.",
        ),
    }
    items = [
        ManagementDashboardAlertHistoryItem(
            event_type=row.event,
            title=title_map.get(row.event, ("Alert action", "Management logged an alert action."))[0],
            description=title_map.get(row.event, ("Alert action", "Management logged an alert action."))[1],
            performed_at=row.created_at,
        )
        for row in rows
    ]
    return ManagementDashboardAlertHistoryOut(success=True, items=items)
