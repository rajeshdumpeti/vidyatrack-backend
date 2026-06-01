from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.core.roles import normalize_role
from app.db.models.attendance_record import AttendanceRecord
from app.db.models.class_ import Class
from app.db.models.fee_payment import FeePayment
from app.db.models.marks_record import MarksRecord
from app.db.models.section import Section
from app.db.models.student import Student
from app.db.models.subject import Subject
from app.db.models.teacher import Teacher
from app.db.models.user import User
from app.db.models.user_school import UserSchool


def _ensure_management_school(db: Session, *, school_id: int, current_user: User) -> None:
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


def get_management_reports(
    db: Session,
    *,
    school_id: int,
    current_user: User,
) -> dict:
    _ensure_management_school(db, school_id=school_id, current_user=current_user)
    today = datetime.now(timezone.utc).date()
    month_start = today.replace(day=1)

    attendance_rows = (
        db.query(
            Class.name.label("class_name"),
            AttendanceRecord.status.label("status"),
            func.count(AttendanceRecord.id).label("count"),
        )
        .join(Student, Student.id == AttendanceRecord.student_id)
        .join(Section, Section.id == Student.section_id, isouter=True)
        .join(Class, Class.id == Section.class_id, isouter=True)
        .filter(
            AttendanceRecord.school_id == school_id,
            AttendanceRecord.date >= month_start,
        )
        .group_by(Class.name, AttendanceRecord.status)
        .all()
    )
    attendance_map: dict[str, dict[str, int]] = defaultdict(lambda: {"present": 0, "absent": 0})
    for row in attendance_rows:
        class_name = row.class_name or "Unassigned"
        status = str(row.status).lower()
        attendance_map[class_name][status] += int(row.count or 0)
    attendance_summary = []
    for class_name, counts in sorted(attendance_map.items(), key=lambda item: item[0]):
        present = counts["present"]
        absent = counts["absent"]
        total = present + absent
        attendance_summary.append(
            {
                "class_name": class_name,
                "present_count": present,
                "absent_count": absent,
                "attendance_pct": round((present / total) * 100, 2) if total else 0.0,
            }
        )

    marks_rows = (
        db.query(
            Subject.name.label("subject_name"),
            MarksRecord.exam_type.label("exam_type"),
            func.avg((MarksRecord.marks_obtained * 100.0) / func.nullif(MarksRecord.max_marks, 0)).label("avg_pct"),
            func.sum(
                case((MarksRecord.marks_obtained >= 35, 1), else_=0)
            ).label("pass_count"),
            func.count(MarksRecord.id).label("total_count"),
        )
        .join(Subject, Subject.id == MarksRecord.subject_id)
        .filter(MarksRecord.school_id == school_id)
        .group_by(Subject.name, MarksRecord.exam_type)
        .order_by(Subject.name.asc(), MarksRecord.exam_type.asc())
        .all()
    )
    exam_summary = [
        {
            "subject_name": row.subject_name or "Unknown",
            "exam_type": row.exam_type,
            "avg_marks_pct": round(float(row.avg_pct or 0), 2),
            "pass_rate_pct": round((int(row.pass_count or 0) / max(int(row.total_count or 0), 1)) * 100, 2),
        }
        for row in marks_rows
    ]

    fee_rows = (
        db.query(
            func.extract("year", FeePayment.payment_date).label("year_num"),
            func.extract("month", FeePayment.payment_date).label("month_num"),
            func.coalesce(func.sum(FeePayment.amount_paid), 0).label("amount"),
            func.count(FeePayment.id).label("count"),
        )
        .filter(FeePayment.school_id == school_id)
        .group_by(
            func.extract("year", FeePayment.payment_date),
            func.extract("month", FeePayment.payment_date),
        )
        .order_by(
            func.extract("year", FeePayment.payment_date).desc(),
            func.extract("month", FeePayment.payment_date).desc(),
        )
        .limit(12)
        .all()
    )
    fee_summary = [
        {
            "month": datetime(
                int(row.year_num or today.year),
                int(row.month_num or today.month),
                1,
            ).strftime("%b %Y"),
            "collected_amount": round(float(row.amount or 0), 2),
            "payment_count": int(row.count or 0),
        }
        for row in fee_rows
    ][::-1]

    teacher_rows = db.query(Teacher).filter(Teacher.school_id == school_id).order_by(Teacher.name.asc()).all()
    principal_rows = (
        db.query(User.full_name.label("name"), UserSchool.role.label("role"))
        .join(UserSchool, UserSchool.user_id == User.id)
        .filter(
            UserSchool.school_id == school_id,
            UserSchool.is_active.is_(True),
            UserSchool.role.ilike("PRINCIPAL"),
        )
        .all()
    )
    staff_summary = [
        {
            "name": row.name,
            "role": "teacher",
            "status": (row.status or "ACTIVE").lower(),
        }
        for row in teacher_rows
    ] + [
        {
            "name": row.name or "Principal",
            "role": str(row.role).lower(),
            "status": "active",
        }
        for row in principal_rows
    ]

    return {
        "success": True,
        "data": {
            "attendance_report": attendance_summary,
            "exam_report": exam_summary,
            "fee_report": fee_summary,
            "staff_report": staff_summary,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
    }
