from __future__ import annotations

import csv
import io

import bcrypt
from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.v1.schemas.management_settings import (
    ManagedUserPasswordResetOut,
    NotificationPreferenceOut,
    NotificationPreferenceUpdateIn,
)
from app.core.roles import normalize_role
from app.db.models.school_features import SchoolFeatures
from app.db.models.student import Student
from app.db.models.user import User
from app.db.models.user_school import UserSchool
from app.services.school_onboarding import _generate_temp_password


DEFAULT_PREFS = {
    "fee_overdue": True,
    "attendance_drop": True,
    "staff_appraisal": True,
    "principal_updates": True,
}


def _ensure_management_access(db: Session, *, school_id: int, current_user: User) -> None:
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


def get_notification_preferences(
    db: Session, *, school_id: int, current_user: User
) -> NotificationPreferenceOut:
    _ensure_management_access(db, school_id=school_id, current_user=current_user)
    row = db.query(SchoolFeatures).filter(SchoolFeatures.school_id == school_id).first()
    prefs = {**DEFAULT_PREFS, **(row.notification_preferences or {})} if row else DEFAULT_PREFS
    return NotificationPreferenceOut(**prefs)


def update_notification_preferences(
    db: Session,
    *,
    school_id: int,
    payload: NotificationPreferenceUpdateIn,
    current_user: User,
) -> NotificationPreferenceOut:
    _ensure_management_access(db, school_id=school_id, current_user=current_user)
    row = db.query(SchoolFeatures).filter(SchoolFeatures.school_id == school_id).first()
    if not row:
      row = SchoolFeatures(school_id=school_id)
    row.notification_preferences = payload.model_dump()
    row.updated_by = current_user.id
    db.add(row)
    db.commit()
    db.refresh(row)
    return NotificationPreferenceOut(**(row.notification_preferences or DEFAULT_PREFS))


def reset_managed_user_password(
    db: Session, *, school_id: int, user_id: int, current_user: User
) -> ManagedUserPasswordResetOut:
    _ensure_management_access(db, school_id=school_id, current_user=current_user)
    mapping = (
        db.query(UserSchool)
        .filter(
            UserSchool.school_id == school_id,
            UserSchool.user_id == user_id,
            UserSchool.is_active.is_(True),
            func.lower(UserSchool.role).in_(["principal", "teacher"]),
        )
        .first()
    )
    if not mapping:
        raise HTTPException(status_code=404, detail={"code": "USER_NOT_FOUND"})

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail={"code": "USER_NOT_FOUND"})

    temp_password = _generate_temp_password()
    user.password_hash = bcrypt.hashpw(temp_password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")
    user.is_first_login = True
    db.add(user)
    db.commit()

    return ManagedUserPasswordResetOut(
        success=True,
        user_id=user.id,
        role=str(mapping.role).lower(),
        full_name=user.full_name,
        login_phone=user.phone,
        login_email=user.email,
        temp_password=temp_password,
    )


def export_students_csv(
    db: Session, *, school_id: int, current_user: User
) -> str:
    _ensure_management_access(db, school_id=school_id, current_user=current_user)
    students = (
        db.query(Student)
        .filter(Student.school_id == school_id)
        .order_by(Student.name.asc())
        .all()
    )
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "student_id",
        "name",
        "parent_name",
        "parent_phone",
        "roll_number",
        "admission_date",
    ])
    for row in students:
        writer.writerow([
            row.id,
            row.name,
            row.parent_name or "",
            row.parent_phone or "",
            row.roll_number or "",
            row.admission_date.isoformat() if row.admission_date else "",
        ])
    return buf.getvalue()
