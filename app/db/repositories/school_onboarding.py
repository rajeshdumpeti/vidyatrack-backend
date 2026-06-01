from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.phone import phone_candidates
from app.db.models.school import School
from app.db.models.school_contact import SchoolContact
from app.db.models.user import User


def normalize_code(value: str) -> str:
    return value.strip().upper()


def find_conflicts(
    db: Session,
    *,
    school_code: str | None,
    udise_code: str | None,
    school_email: str | None,
    admin_phone: str | None,
    admin_email: str | None,
) -> list[str]:
    conflicts: list[str] = []

    if school_code:
        code = normalize_code(school_code)
        exists = db.query(School.id).filter(School.code == code).first()
        if exists:
            conflicts.append("SCHOOL_CODE_ALREADY_EXISTS")

    if udise_code:
        normalized_udise = udise_code.strip()
        exists = db.query(School.id).filter(func.trim(School.udise_code) == normalized_udise).first()
        if exists:
            conflicts.append("UDISE_CODE_ALREADY_EXISTS")

    if school_email:
        normalized_email = school_email.strip().lower()
        exists = (
            db.query(SchoolContact.id)
            .filter(func.lower(func.trim(SchoolContact.school_email)) == normalized_email)
            .first()
        )
        if exists:
            conflicts.append("SCHOOL_EMAIL_ALREADY_EXISTS")

    if admin_phone:
        exists = (
            db.query(User.id)
            .filter(User.phone.in_(phone_candidates(admin_phone)))
            .first()
        )
        if exists:
            conflicts.append("ADMIN_PHONE_ALREADY_EXISTS")

    if admin_email:
        normalized_admin_email = admin_email.strip().lower()
        exists = (
            db.query(User.id)
            .filter(func.lower(func.trim(User.email)) == normalized_admin_email)
            .first()
        )
        if exists:
            conflicts.append("ADMIN_EMAIL_ALREADY_EXISTS")

    return conflicts


def count_schools_created_by(db: Session, user_id: int) -> int:
    return db.query(School.id).filter(School.created_by == user_id).count()
