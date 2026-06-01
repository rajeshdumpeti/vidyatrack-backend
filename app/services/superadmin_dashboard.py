"""
Super Admin platform dashboard service.

Queries are intentionally kept to plain SQLAlchemy Core/ORM — no raw SQL —
so they work on both PostgreSQL (prod) and SQLite (tests).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.school import School
from app.db.models.student import Student
from app.db.models.user import User
from app.db.models.user_school import UserSchool
from app.db.models.audit_log import AuditLog


def get_platform_dashboard(db: Session) -> dict[str, Any]:
    now = datetime.now(timezone.utc)

    # ── 1. Count teachers per school (role=TEACHER, is_active=True) ──────────
    teacher_counts = (
        db.execute(
            select(
                UserSchool.school_id,
                func.count(UserSchool.user_id).label("cnt"),
            )
            .where(
                UserSchool.role.ilike("TEACHER"),
                UserSchool.is_active.is_(True),
            )
            .group_by(UserSchool.school_id)
        )
        .mappings()
        .all()
    )
    teachers_by_school: dict[int, int] = {r["school_id"]: r["cnt"] for r in teacher_counts}

    # ── 2. Count students per school ─────────────────────────────────────────
    student_counts = (
        db.execute(
            select(
                Student.school_id,
                func.count(Student.id).label("cnt"),
            )
            .group_by(Student.school_id)
        )
        .mappings()
        .all()
    )
    students_by_school: dict[int, int] = {r["school_id"]: r["cnt"] for r in student_counts}

    # ── 3. Management admins who have never logged in ────────────────────────
    mgmt_never_rows = (
        db.execute(
            select(
                UserSchool.school_id,
                UserSchool.user_id,
            )
            .join(User, User.id == UserSchool.user_id)
            .where(
                UserSchool.role.ilike("MANAGEMENT"),
                UserSchool.is_active.is_(True),
                User.last_login_at.is_(None),
            )
        )
        .mappings()
        .all()
    )
    never_logged_school_ids: set[int] = {r["school_id"] for r in mgmt_never_rows}

    # ── 4. All active schools ─────────────────────────────────────────────────
    active_schools = (
        db.execute(
            select(School).where(School.status.ilike("ACTIVE"))
        )
        .scalars()
        .all()
    )

    total_schools = len(active_schools)
    total_teachers = sum(teachers_by_school.values())
    total_students = sum(students_by_school.values())
    schools_never_logged_in = len(never_logged_school_ids)

    # ── 5. Build alert list ───────────────────────────────────────────────────
    alerts: list[dict[str, Any]] = []

    for school in active_schools:
        t = teachers_by_school.get(school.id, 0)
        s = students_by_school.get(school.id, 0)
        days_since = (now - school.created_at.replace(tzinfo=timezone.utc)).days if school.created_at else 0

        if t == 0 or s == 0:
            alerts.append({
                "school_id": str(school.internal_id),
                "school_name": school.name,
                "alert_type": "setup_incomplete",
                "severity": "critical" if days_since > 7 else "warning",
                "message": (
                    "No teachers and no students registered."
                    if t == 0 and s == 0
                    else f"No {'teachers' if t == 0 else 'students'} registered yet."
                ),
                "days_since_created": days_since,
                "action_url": f"/superadmin/schools/{school.internal_id}",
            })

        if school.id in never_logged_school_ids:
            alerts.append({
                "school_id": str(school.internal_id),
                "school_name": school.name,
                "alert_type": "never_logged_in",
                "severity": "warning",
                "message": "Management Admin has never logged in. Credentials may not have been received.",
                "days_since_created": days_since,
                "action_url": f"/superadmin/schools/{school.internal_id}",
            })

    # Sort: critical first, then by days_since desc
    alerts.sort(key=lambda a: (0 if a["severity"] == "critical" else 1, -a["days_since_created"]))

    # ── 6. Recent activity from audit_logs ────────────────────────────────────
    recent_logs = (
        db.execute(
            select(AuditLog, User)
            .outerjoin(User, User.id == AuditLog.user_id)
            .order_by(AuditLog.created_at.desc())
            .limit(20)
        )
        .all()
    )

    # Build school name map from user→school via UserSchool
    user_school_map: dict[int, str] = {}
    if recent_logs:
        user_ids = [row[0].user_id for row in recent_logs if row[0].user_id]
        if user_ids:
            us_rows = (
                db.execute(
                    select(UserSchool.user_id, School.name)
                    .join(School, School.id == UserSchool.school_id)
                    .where(UserSchool.user_id.in_(user_ids), UserSchool.is_active.is_(True))
                )
                .mappings()
                .all()
            )
            for row in us_rows:
                if row["user_id"] not in user_school_map:
                    user_school_map[row["user_id"]] = row["name"]

    _event_label = {
        "login_success": "Logged in",
        "login_failure": "Failed login attempt",
        "login_locked": "Account locked",
        "password_reset_requested": "Password reset requested",
        "password_reset_complete": "Password reset completed",
    }

    recent_activity = []
    for log, user in recent_logs:
        school_name = (
            user_school_map.get(log.user_id, "Unknown School")
            if log.user_id else "Unknown School"
        )
        performed_by = user.full_name or log.identifier or "Unknown" if user else (log.identifier or "Unknown")
        recent_activity.append({
            "event_type": log.event,
            "school_name": school_name,
            "description": _event_label.get(log.event, log.event.replace("_", " ").title()),
            "performed_by": performed_by,
            "performed_at": log.created_at.isoformat() if log.created_at else None,
        })

    return {
        "success": True,
        "data": {
            "platform_summary": {
                "total_schools": total_schools,
                "pilot_schools": total_schools,  # all are pilot during this phase
                "schools_setup_incomplete": sum(
                    1 for s in active_schools
                    if teachers_by_school.get(s.id, 0) == 0 or students_by_school.get(s.id, 0) == 0
                ),
                "schools_never_logged_in": schools_never_logged_in,
                "total_teachers": total_teachers,
                "total_students": total_students,
                "last_updated": now.isoformat(),
            },
            "alerts": alerts,
            "recent_activity": recent_activity,
        },
    }
