"""
Super Admin — school directory service.

GET /api/v1/superadmin/schools with search, filter, sort, pagination.
"""
from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select, or_
from sqlalchemy.orm import Session

from app.db.models.school import School
from app.db.models.student import Student
from app.db.models.user import User
from app.db.models.user_school import UserSchool


def _initials(name: str) -> str:
    parts = name.strip().split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[-1][0]).upper()
    return name[:2].upper() if len(name) >= 2 else name[0].upper()


def _relative_time(dt: datetime | None) -> str | None:
    if not dt:
        return None
    now = datetime.now(timezone.utc)
    aware = dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    diff = now - aware
    days = diff.days
    if days == 0:
        hrs = diff.seconds // 3600
        return "today" if hrs == 0 else f"{hrs}h ago"
    if days == 1:
        return "yesterday"
    if days < 30:
        return f"{days}d ago"
    months = days // 30
    return f"{months}mo ago"


def _setup_pct(teacher_count: int, student_count: int) -> int:
    """
    Simple 4-step completion score:
      school registered       = 25%
      management admin exists = 25%  (always true if we can query it)
      ≥1 teacher              = 25%
      ≥1 student              = 25%
    """
    score = 50  # registered + management admin (assumed if school exists)
    if teacher_count > 0:
        score += 25
    if student_count > 0:
        score += 25
    return score


def _normalize_status(raw: str | None) -> str:
    if not raw:
        return "active"
    return raw.strip().lower()


def get_superadmin_schools(
    db: Session,
    *,
    search: str | None = None,
    status_filter: str = "all",
    setup_filter: str = "all",
    show_test: bool = False,
    page: int = 1,
    per_page: int = 20,
    sort_by: str = "created_at",
    sort_order: str = "desc",
) -> dict[str, Any]:

    # ── teacher counts per school ─────────────────────────────────────────────
    teacher_sq = (
        select(
            UserSchool.school_id,
            func.count(UserSchool.user_id).label("cnt"),
        )
        .where(UserSchool.role.ilike("TEACHER"), UserSchool.is_active.is_(True))
        .group_by(UserSchool.school_id)
        .subquery()
    )

    # ── student counts per school ─────────────────────────────────────────────
    student_sq = (
        select(
            Student.school_id,
            func.count(Student.id).label("cnt"),
        )
        .group_by(Student.school_id)
        .subquery()
    )

    # ── management admin per school (first active management user) ────────────
    mgmt_sq = (
        select(
            UserSchool.school_id,
            func.min(User.id).label("user_id"),
        )
        .join(User, User.id == UserSchool.user_id)
        .where(UserSchool.role.ilike("MANAGEMENT"), UserSchool.is_active.is_(True))
        .group_by(UserSchool.school_id)
        .subquery()
    )

    # ── base query ────────────────────────────────────────────────────────────
    stmt = (
        select(
            School,
            func.coalesce(teacher_sq.c.cnt, 0).label("teacher_count"),
            func.coalesce(student_sq.c.cnt, 0).label("student_count"),
            User.full_name.label("mgmt_name"),
            User.phone.label("mgmt_phone"),
            User.last_login_at.label("mgmt_last_login"),
        )
        .outerjoin(teacher_sq, teacher_sq.c.school_id == School.id)
        .outerjoin(student_sq, student_sq.c.school_id == School.id)
        .outerjoin(mgmt_sq, mgmt_sq.c.school_id == School.id)
        .outerjoin(User, User.id == mgmt_sq.c.user_id)
    )

    # ── filters ───────────────────────────────────────────────────────────────
    if search:
        like = f"%{search}%"
        stmt = stmt.where(
            or_(School.name.ilike(like), School.code.ilike(like))
        )

    if status_filter != "all":
        stmt = stmt.where(School.status.ilike(status_filter))
    else:
        # exclude hard-deleted by default
        stmt = stmt.where(School.status.notin_(["DELETED", "deleted"]))

    # test schools: schools whose name or code contains test/demo keywords
    _test_keywords = ["test", "demo", "sample", "dummy"]
    _test_conditions = [
        or_(School.name.ilike(f"%{kw}%"), School.code.ilike(f"%{kw}%"))
        for kw in _test_keywords
    ]
    _is_test_expr = or_(*_test_conditions)

    if not show_test:
        stmt = stmt.where(School.is_test.is_(False), ~_is_test_expr)

    # ── summary counts (before setup filter, after status/test/search) ────────

    # For summary we always look at all active schools regardless of filters
    all_active = db.execute(
        select(func.count()).where(School.status.ilike("ACTIVE"))
    ).scalar_one()
    all_pilot = db.execute(
        select(func.count()).where(School.plan_type.ilike("pilot"))
    ).scalar_one()
    incomplete_sq = (
        select(func.count(School.id))
        .outerjoin(teacher_sq, teacher_sq.c.school_id == School.id)
        .outerjoin(student_sq, student_sq.c.school_id == School.id)
        .where(
            School.status.notin_(["DELETED", "deleted"]),
            or_(
                func.coalesce(teacher_sq.c.cnt, 0) == 0,
                func.coalesce(student_sq.c.cnt, 0) == 0,
            ),
        )
    )
    all_incomplete = db.execute(incomplete_sq).scalar_one()

    # ── setup filter (applied after summary) ──────────────────────────────────
    if setup_filter == "complete":
        stmt = stmt.where(
            func.coalesce(teacher_sq.c.cnt, 0) > 0,
            func.coalesce(student_sq.c.cnt, 0) > 0,
        )
    elif setup_filter == "incomplete":
        stmt = stmt.where(
            or_(
                func.coalesce(teacher_sq.c.cnt, 0) == 0,
                func.coalesce(student_sq.c.cnt, 0) == 0,
            )
        )

    # ── total after all filters ───────────────────────────────────────────────
    total_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.execute(total_stmt).scalar_one()

    # ── sorting ───────────────────────────────────────────────────────────────
    _sort_col_map = {
        "name": School.name,
        "created_at": School.created_at,
        "student_count": func.coalesce(student_sq.c.cnt, 0),
        "last_active": User.last_login_at,
    }
    sort_col = _sort_col_map.get(sort_by, School.created_at)
    stmt = stmt.order_by(sort_col.desc() if sort_order ==
                         "desc" else sort_col.asc())

    # ── pagination ────────────────────────────────────────────────────────────
    offset = (page - 1) * per_page
    stmt = stmt.offset(offset).limit(per_page)

    rows = db.execute(stmt).all()

    # ── serialize ─────────────────────────────────────────────────────────────
    schools_out = []
    for school, t_count, s_count, mgmt_name, mgmt_phone, mgmt_last_login in rows:
        t_count = t_count or 0
        s_count = s_count or 0

        school_name_lower = school.name.lower()
        code_lower = (school.code or "").lower()
        is_test = bool(school.is_test) or any(
            kw in school_name_lower or kw in code_lower for kw in _test_keywords
        )

        mgmt_login_aware = None
        if mgmt_last_login:
            mgmt_login_aware = (
                mgmt_last_login
                if mgmt_last_login.tzinfo
                else mgmt_last_login.replace(tzinfo=timezone.utc)
            )

        schools_out.append({
            "id": str(school.internal_id),
            "vt_school_id": school.public_id,
            "name": school.name,
            "initials": _initials(school.name),
            "status": _normalize_status(school.status),
            "plan_type": (school.plan_type or "pilot").lower(),
            "is_test": is_test,
            "setup_completion_pct": _setup_pct(t_count, s_count),
            "stats": {
                "total_teachers": t_count,
                "total_students": s_count,
            },
            "management_admin": {
                "full_name": mgmt_name,
                "phone": mgmt_phone,
                "last_login_at": mgmt_login_aware.isoformat() if mgmt_login_aware else None,
                "last_login_relative": (
                    _relative_time(
                        mgmt_login_aware) if mgmt_login_aware else "Never logged in"
                ),
            },
            "created_at": (
                school.created_at.isoformat() if school.created_at else None
            ),
            "last_activity_at": (
                mgmt_login_aware.isoformat() if mgmt_login_aware else None
            ),
        })

    return {
        "success": True,
        "data": {
            "summary": {
                "total": all_active,
                "active": all_active,
                "pilot": all_pilot,
                "setup_incomplete": all_incomplete,
            },
            "schools": schools_out,
            "pagination": {
                "total": total,
                "page": page,
                "per_page": per_page,
                "total_pages": max(1, math.ceil(total / per_page)),
            },
        },
    }
