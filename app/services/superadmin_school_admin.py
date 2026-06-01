from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.phone import normalize_phone
from app.core.roles import normalize_role
from app.db.models.management_admin import ManagementAdmin
from app.db.models.school import School
from app.db.models.school_academic_details import SchoolAcademicDetails
from app.db.models.school_contact import SchoolContact
from app.db.models.school_features import SchoolFeatures
from app.db.models.school_grade import SchoolGrade
from app.db.models.section import Section
from app.db.models.subject import Subject
from app.db.models.teacher import Teacher
from app.db.models.class_ import Class
from app.db.models.fee_structure import FeeStructure
from app.db.models.student import Student
from app.db.models.audit_log import AuditLog
from app.db.models.user import User
from app.db.models.user_school import UserSchool
from app.integrations.email.brevo import send_credentials_email
from app.integrations.whatsapp.client import send_credentials_sms, send_school_status_sms
from app.services.school_onboarding import _generate_temp_password
from app.services.public_id import next_public_id


PRD_MODULES = [
    "attendance",
    "exams",
    "fees",
    "library",
    "transport",
    "hostel",
    "hr",
    "accounting",
    "communication",
    "reports",
]


def _month_to_int(value: str) -> int | None:
    if value is None:
        return None
    key = str(value).strip().lower()
    mapping = {
        "january": 1,
        "february": 2,
        "march": 3,
        "april": 4,
        "may": 5,
        "june": 6,
        "july": 7,
        "august": 8,
        "september": 9,
        "october": 10,
        "november": 11,
        "december": 12,
    }
    if key in mapping:
        return mapping[key]
    return None


def _normalize_class_levels(levels: list[str]) -> list[str]:
    out: list[str] = []
    for raw in levels or []:
        token = str(raw).strip()
        if not token:
            continue
        key = token.lower().replace("-", "_").replace(" ", "_")
        if key == "pre_nursery":
            out.append("Pre Nursery")
        elif key == "lkg":
            out.append("LKG")
        elif key == "ukg":
            out.append("UKG")
        else:
            out.append(token)
    seen: set[str] = set()
    deduped: list[str] = []
    for item in out:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return deduped


def _grade_row(level_name: str) -> tuple[str, str, int | None]:
    cleaned = str(level_name).strip()
    normalized = cleaned.upper().replace(" ", "_")
    if normalized in {"PRE_NURSERY", "PRE-NURSERY"}:
        return ("Pre Nursery", "PREN", -1)
    if normalized == "LKG":
        return ("LKG", "LKG", 0)
    if normalized == "UKG":
        return ("UKG", "UKG", 1)
    if cleaned.isdigit():
        return (f"Grade {int(cleaned)}", f"GR{int(cleaned)}", int(cleaned) + 1)
    code = "".join(ch for ch in cleaned.upper() if ch.isalnum())[:10] or "GRD"
    return (cleaned, code, None)


def _resolve_school(db: Session, school_id: str) -> School:
    raw = (school_id or "").strip()
    if not raw:
        raise HTTPException(status_code=404, detail={"code": "SCHOOL_NOT_FOUND"})
    # UUID (internal_id)
    try:
        internal = uuid.UUID(raw)
        school = db.query(School).filter(School.internal_id == internal).first()
        if school:
            return school
    except Exception:
        pass
    # int id
    if raw.isdigit():
        school = db.query(School).filter(School.id == int(raw)).first()
        if school:
            return school
    # VT public id
    school = db.query(School).filter(School.public_id == raw).first()
    if school:
        return school
    raise HTTPException(status_code=404, detail={"code": "SCHOOL_NOT_FOUND"})


def get_school_detail(db: Session, *, school_id: str) -> dict[str, Any]:
    school = _resolve_school(db, school_id)

    contact = db.query(SchoolContact).filter(SchoolContact.school_id == school.id).first()
    academic = (
        db.query(SchoolAcademicDetails)
        .filter(SchoolAcademicDetails.school_id == school.id)
        .first()
    )
    features = (
        db.query(SchoolFeatures).filter(SchoolFeatures.school_id == school.id).first()
    )

    mgmt_user = (
        db.query(User)
        .join(UserSchool, UserSchool.user_id == User.id)
        .filter(
            UserSchool.school_id == school.id,
            UserSchool.role.ilike("MANAGEMENT"),
            UserSchool.is_active.is_(True),
        )
        .order_by(User.id.asc())
        .first()
    )
    mgmt_profile = None
    if mgmt_user:
        mgmt_profile = (
            db.query(ManagementAdmin)
            .filter(ManagementAdmin.school_id == school.id, ManagementAdmin.user_id == mgmt_user.id)
            .first()
        )

    teacher_count = (
        db.execute(
            select(func.count(UserSchool.user_id))
            .where(
                UserSchool.school_id == school.id,
                UserSchool.role.ilike("TEACHER"),
                UserSchool.is_active.is_(True),
            )
        )
        .scalar_one()
    )
    student_count = (
        db.execute(select(func.count(Student.id)).where(Student.school_id == school.id)).scalar_one()
    )
    staff_count = (
        db.execute(
            select(func.count(UserSchool.user_id))
            .where(
                UserSchool.school_id == school.id,
                UserSchool.role.notilike("TEACHER"),
                UserSchool.role.notilike("STUDENT"),
                UserSchool.is_active.is_(True),
            )
        )
        .scalar_one()
    )

    class_count = db.execute(select(func.count(Class.id)).where(Class.school_id == school.id)).scalar_one()
    section_count = db.execute(select(func.count(Section.id)).where(Section.school_id == school.id)).scalar_one()
    subject_count = db.execute(select(func.count(Subject.id)).where(Subject.school_id == school.id)).scalar_one()
    fee_structure_count = db.execute(
        select(func.count(FeeStructure.id)).where(FeeStructure.school_id == school.id, FeeStructure.is_active.is_(True))
    ).scalar_one()

    modules_enabled = set((features.modules_enabled or []) if features else [])
    modules = {m: (m in modules_enabled) for m in PRD_MODULES}

    grades = (
        db.query(SchoolGrade)
        .filter(SchoolGrade.school_id == school.id, SchoolGrade.is_active.is_(True))
        .order_by(SchoolGrade.grade_level.asc().nulls_last(), SchoolGrade.id.asc())
        .all()
    )

    # Setup completion breakdown (PRD 6.1.1)
    setup_steps = [
        ("classes_added", int(class_count or 0) > 0),
        ("sections_added", int(section_count or 0) > 0),
        ("subjects_added", int(subject_count or 0) > 0),
        ("teachers_registered", int(teacher_count or 0) > 0),
        ("students_enrolled", int(student_count or 0) > 0),
        ("fee_structure_set", int(fee_structure_count or 0) > 0),
    ]
    completed = sum(1 for _, ok in setup_steps if ok)
    setup_pct = int(round((completed / max(1, len(setup_steps))) * 100))
    setup_breakdown = {k: v for k, v in setup_steps}

    # Recent activity feed (last 10 actions in this school)
    mapped_user_ids = (
        db.execute(
            select(UserSchool.user_id)
            .where(UserSchool.school_id == school.id, UserSchool.is_active.is_(True))
        )
        .scalars()
        .all()
    )
    log_rows = (
        db.execute(
            select(AuditLog, User)
            .outerjoin(User, User.id == AuditLog.user_id)
            .where(
                (AuditLog.user_id.in_(mapped_user_ids)) if mapped_user_ids else False
            )
            .order_by(AuditLog.created_at.desc())
            .limit(10)
        )
        .all()
    )
    # Include school-scoped logs written with identifier=school.public_id (super admin actions)
    school_logs = (
        db.execute(
            select(AuditLog, User)
            .outerjoin(User, User.id == AuditLog.user_id)
            .where(AuditLog.identifier == school.public_id)
            .order_by(AuditLog.created_at.desc())
            .limit(10)
        )
        .all()
    )
    merged = {}
    for row in list(log_rows) + list(school_logs):
        log = row[0]
        merged[log.id] = row
    merged_rows = sorted(merged.values(), key=lambda r: r[0].created_at or datetime.min.replace(tzinfo=timezone.utc), reverse=True)[:10]

    _event_label = {
        "SCHOOL_ONBOARDED": "School onboarded",
        "SCHOOL_MODULES_UPDATED": "Modules updated",
        "SCHOOL_EDITED": "School details updated",
        "login_success": "Logged in",
        "login_failure": "Failed login attempt",
        "password_reset_requested": "Password reset requested",
        "password_reset_complete": "Password reset completed",
        "fee_head_created": "Fee head created",
        "fee_structure_created": "Fee structure created",
    }
    recent_activity = []
    for log, user in merged_rows:
        performed_by = None
        if user:
            performed_by = user.full_name or user.email or user.phone
        performed_by = performed_by or log.identifier or "Unknown"
        recent_activity.append({
            "event_type": log.event,
            "description": _event_label.get(log.event, (log.event or "").replace("_", " ").title()),
            "performed_by": performed_by,
            "performed_at": log.created_at.isoformat() if log.created_at else None,
        })

    return {
        "success": True,
        "data": {
            "school": {
                "id": str(school.internal_id),
                "vt_school_id": school.public_id,
                "name": school.name,
                "school_code": school.code,
                "status": school.status.lower(),
                "plan_type": (school.plan_type or "pilot").lower(),
                "is_test": bool(school.is_test),
                "created_at": school.created_at.isoformat() if school.created_at else None,
                "suspended_at": school.suspended_at.isoformat() if school.suspended_at else None,
                "suspension_reason": school.suspension_reason,
                "board": school.board,
                "category": school.category,
                "medium": school.medium,
                "school_type": school.school_type,
                "established_year": school.established_year,
                "affiliation_number": school.affiliation_number,
                "udise_code": school.udise_code,
            },
            "setup": {
                "setup_completion_pct": setup_pct,
                "breakdown": setup_breakdown,
                "counts": {
                    "classes": int(class_count or 0),
                    "sections": int(section_count or 0),
                    "subjects": int(subject_count or 0),
                    "teachers": int(teacher_count or 0),
                    "students": int(student_count or 0),
                    "fee_structures": int(fee_structure_count or 0),
                },
            },
            "management_admin": (
                {
                    "user_id": str(mgmt_user.internal_id) if mgmt_user else None,
                    "full_name": mgmt_user.full_name if mgmt_user else None,
                    "phone": mgmt_user.phone if mgmt_user else None,
                    "email": mgmt_user.email if mgmt_user else None,
                    "first_name": mgmt_profile.first_name if mgmt_profile else None,
                    "last_name": mgmt_profile.last_name if mgmt_profile else None,
                    "designation": mgmt_profile.designation if mgmt_profile else None,
                    "department": mgmt_profile.department if mgmt_profile else None,
                    "employee_id": mgmt_profile.employee_id if mgmt_profile else None,
                    "last_login_at": mgmt_user.last_login_at.isoformat() if mgmt_user and mgmt_user.last_login_at else None,
                    "never_logged_in": bool(mgmt_user and mgmt_user.last_login_at is None),
                }
                if mgmt_user
                else None
            ),
            "stats": {
                "total_students": int(student_count or 0),
                "total_teachers": int(teacher_count or 0),
                "total_staff": int(staff_count or 0),
                "total_registered": int((student_count or 0) + (teacher_count or 0) + (staff_count or 0)),
            },
            "recent_activity": recent_activity,
            "academic": {
                "current_session": academic.current_session if academic else None,
                "academic_start_month": academic.academic_start_month if academic else None,
                "academic_end_month": academic.academic_end_month if academic else None,
                "working_days_per_week": academic.working_days_per_week if academic else None,
                "class_levels": academic.class_levels if academic else [],
                "grades": [{"grade_name": g.grade_name, "grade_code": g.grade_code} for g in grades],
            },
            "contact": {
                "street_address": contact.street if contact else None,
                "area": contact.area if contact else None,
                "city": contact.city if contact else None,
                "district": contact.district if contact else None,
                "state": contact.state if contact else None,
                "pincode": contact.pin_code if contact else None,
                "country": contact.country if contact else None,
                "landmark": contact.landmark if contact else None,
                "latitude": float(contact.latitude) if contact and contact.latitude is not None else None,
                "longitude": float(contact.longitude) if contact and contact.longitude is not None else None,
                "school_phone": contact.school_phone if contact else None,
                "school_email": contact.school_email if contact else None,
                "website": contact.website if contact else None,
            },
            "modules_limits": {
                "modules": modules,
                "limits": {
                    "max_students": features.max_students if features else None,
                    "max_teachers": features.max_teachers if features else None,
                    "max_staff": features.max_staff if features else None,
                    "storage_limit_gb": features.storage_limit_gb if features else None,
                },
                "features": {
                    "api_access": features.api_access if features else False,
                    "bulk_operations": features.bulk_operations if features else False,
                    "custom_reports": features.custom_reports if features else False,
                },
            },
        },
    }


def reset_management_password(
    db: Session,
    *,
    school_id: str,
    user_id: str,
    send_via: Literal["sms", "email", "both"] = "sms",
    reason: str | None = None,
) -> dict[str, Any]:
    school = _resolve_school(db, school_id)

    try:
        target_uuid = uuid.UUID(user_id)
        user = db.query(User).filter(User.internal_id == target_uuid).first()
    except Exception:
        user = None
    if user is None and user_id.isdigit():
        user = db.query(User).filter(User.id == int(user_id)).first()

    if not user:
        raise HTTPException(status_code=404, detail={"code": "USER_NOT_FOUND"})

    mapping = (
        db.query(UserSchool)
        .filter(
            UserSchool.school_id == school.id,
            UserSchool.user_id == user.id,
            UserSchool.role.ilike("MANAGEMENT"),
            UserSchool.is_active.is_(True),
        )
        .first()
    )
    if not mapping:
        raise HTTPException(status_code=400, detail={"code": "USER_NOT_MANAGEMENT_ADMIN"})

    import bcrypt as _bcrypt

    temp_password = _generate_temp_password()
    user.password_hash = _bcrypt.hashpw(temp_password.encode("utf-8"), _bcrypt.gensalt(rounds=12)).decode("utf-8")
    user.is_first_login = True
    user.failed_login_attempts = 0
    user.locked_until = None
    db.add(user)
    db.commit()

    sms_delivered = False
    email_delivered = False

    if send_via in ("sms", "both"):
        sms_result = send_credentials_sms(
            user.phone,
            school_name=school.name,
            admin_name=user.full_name or "Admin",
            temp_password=temp_password,
        )
        sms_delivered = sms_result.success

    if send_via in ("email", "both") and user.email:
        email_result = send_credentials_email(
            user.email,
            school_name=school.name,
            admin_name=user.full_name or "Admin",
            phone=user.phone,
            temp_password=temp_password,
        )
        email_delivered = email_result.success

    return {
        "success": True,
        "data": {
            "temporary_password": temp_password,
            "sms_sent_to": user.phone if sms_delivered else None,
            "email_sent_to": user.email if email_delivered else None,
            "note": "User will be forced to change password on next login",
            "reason": reason,
        },
    }


def suspend_school(
    db: Session,
    *,
    school_id: str,
    reason: str,
    notify_management: bool = True,
) -> dict[str, Any]:
    school = _resolve_school(db, school_id)
    school.status = "SUSPENDED"
    school.suspended_at = datetime.now(timezone.utc)
    school.suspension_reason = reason
    db.add(school)
    db.commit()

    sms_delivered = False
    if notify_management:
        mgmt_phone = (
            db.query(User.phone)
            .join(UserSchool, UserSchool.user_id == User.id)
            .filter(
                UserSchool.school_id == school.id,
                UserSchool.role.ilike("MANAGEMENT"),
                UserSchool.is_active.is_(True),
            )
            .scalar()
        )
        if mgmt_phone:
            sms_delivered = send_school_status_sms(
                mgmt_phone,
                school_name=school.name,
                status_label="SUSPENDED",
                reason=reason,
            ).success

    return {
        "success": True,
        "data": {
            "school_id": str(school.internal_id),
            "status": "suspended",
            "notify_management": notify_management,
            "sms_delivered": sms_delivered,
        },
    }


def reactivate_school(
    db: Session,
    *,
    school_id: str,
    notify_management: bool = True,
) -> dict[str, Any]:
    school = _resolve_school(db, school_id)
    plan = (school.plan_type or "pilot").lower()
    school.status = "PILOT" if plan == "pilot" else "ACTIVE"
    school.suspended_at = None
    school.suspension_reason = None
    db.add(school)
    db.commit()

    sms_delivered = False
    if notify_management:
        mgmt_phone = (
            db.query(User.phone)
            .join(UserSchool, UserSchool.user_id == User.id)
            .filter(
                UserSchool.school_id == school.id,
                UserSchool.role.ilike("MANAGEMENT"),
                UserSchool.is_active.is_(True),
            )
            .scalar()
        )
        if mgmt_phone:
            sms_delivered = send_school_status_sms(
                mgmt_phone,
                school_name=school.name,
                status_label="ACTIVE",
                reason=None,
            ).success

    return {
        "success": True,
        "data": {
            "school_id": str(school.internal_id),
            "status": school.status.lower(),
            "notify_management": notify_management,
            "sms_delivered": sms_delivered,
        },
    }


def mark_school_test_flag(db: Session, *, school_id: str, is_test: bool) -> dict[str, Any]:
    school = _resolve_school(db, school_id)
    school.is_test = bool(is_test)
    db.add(school)
    db.commit()
    return {"success": True, "data": {"school_id": str(school.internal_id), "is_test": bool(school.is_test)}}


def update_school_modules(
    db: Session,
    *,
    school_id: str,
    modules: dict[str, bool],
    current_user: User,
) -> dict[str, Any]:
    """
    Update enabled modules for a school (Super Admin only).
    Stores the enabled module codes in SchoolFeatures.modules_enabled.
    """
    school = _resolve_school(db, school_id)

    if not isinstance(modules, dict):
        raise HTTPException(status_code=422, detail={"code": "INVALID_MODULES_PAYLOAD"})

    allowed = set(PRD_MODULES)
    unknown = [k for k in modules.keys() if k not in allowed]
    if unknown:
        raise HTTPException(
            status_code=422,
            detail={"code": "INVALID_MODULES", "unknown": sorted(unknown)},
        )

    enabled = sorted([k for k, v in modules.items() if bool(v)])

    features = db.query(SchoolFeatures).filter(SchoolFeatures.school_id == school.id).first()
    if not features:
        features = SchoolFeatures(school_id=school.id)
    features.modules_enabled = enabled
    db.add(features)

    db.add(
        AuditLog(
            user_id=current_user.id,
            event="SCHOOL_MODULES_UPDATED",
            identifier=school.public_id,
        )
    )
    db.commit()

    return {
        "success": True,
        "data": {
            "school_id": str(school.internal_id),
            "modules_enabled": enabled,
            "modules": {m: (m in set(enabled)) for m in PRD_MODULES},
        },
    }


def update_school_from_prd_payload(
    db: Session,
    *,
    school_id: str,
    payload: dict[str, Any],
    current_user: User,
) -> dict[str, Any]:
    """
    Production-grade edit handler for PRD 6.2.
    Accepts the same nested payload as create and updates all related rows.
    """
    school = _resolve_school(db, school_id)

    si = payload["school_identity"]
    lc = payload["location_contact"]
    ma = payload["management_admin"]
    ab = payload["academic_baseline"]
    ml = payload["modules_limits"]
    pi = payload["plan_info"]

    # Resolve related rows
    contact = db.query(SchoolContact).filter(SchoolContact.school_id == school.id).first()
    if not contact:
        contact = SchoolContact(school_id=school.id)
    academic = db.query(SchoolAcademicDetails).filter(SchoolAcademicDetails.school_id == school.id).first()
    if not academic:
        academic = SchoolAcademicDetails(school_id=school.id)
    features = db.query(SchoolFeatures).filter(SchoolFeatures.school_id == school.id).first()
    if not features:
        features = SchoolFeatures(school_id=school.id)

    mgmt_user = (
        db.query(User)
        .join(UserSchool, UserSchool.user_id == User.id)
        .filter(
            UserSchool.school_id == school.id,
            UserSchool.role.ilike("MANAGEMENT"),
            UserSchool.is_active.is_(True),
        )
        .order_by(User.id.asc())
        .first()
    )
    if not mgmt_user:
        raise HTTPException(status_code=400, detail={"code": "MANAGEMENT_ADMIN_NOT_FOUND"})
    mgmt_profile = (
        db.query(ManagementAdmin)
        .filter(ManagementAdmin.school_id == school.id, ManagementAdmin.user_id == mgmt_user.id)
        .first()
    )
    if not mgmt_profile:
        mgmt_profile = ManagementAdmin(
            school_id=school.id,
            user_id=mgmt_user.id,
            public_id=next_public_id(db, tenant_code=school.code, entity="management_admin"),
        )

    # --- conflict checks (exclude current) ---
    school_email = (lc.get("school_email") or "").strip().lower()
    if school_email:
        email_exists = (
            db.query(SchoolContact.id)
            .filter(func.lower(func.trim(SchoolContact.school_email)) == school_email, SchoolContact.school_id != school.id)
            .first()
        )
        if email_exists:
            raise HTTPException(status_code=409, detail={"code": "CONFLICT", "conflicts": ["SCHOOL_EMAIL_ALREADY_EXISTS"]})

    udise_code = (si.get("udise_code") or "").strip()
    if udise_code:
        udise_exists = (
            db.query(School.id)
            .filter(func.trim(School.udise_code) == udise_code, School.id != school.id)
            .first()
        )
        if udise_exists:
            raise HTTPException(status_code=409, detail={"code": "CONFLICT", "conflicts": ["UDISE_CODE_ALREADY_EXISTS"]})

    admin_phone = normalize_phone(ma["phone"])
    phone_exists = db.query(User.id).filter(User.phone == admin_phone, User.id != mgmt_user.id).first()
    if phone_exists:
        raise HTTPException(status_code=409, detail={"code": "CONFLICT", "conflicts": ["ADMIN_PHONE_ALREADY_EXISTS"]})

    admin_email = (ma.get("email") or "").strip().lower()
    if admin_email:
        email_user_exists = (
            db.query(User.id)
            .filter(func.lower(func.trim(User.email)) == admin_email, User.id != mgmt_user.id)
            .first()
        )
        if email_user_exists:
            raise HTTPException(status_code=409, detail={"code": "CONFLICT", "conflicts": ["ADMIN_EMAIL_ALREADY_EXISTS"]})

    # --- update school identity ---
    school.name = si["school_name"].strip()
    school.board = si["board"]
    school.category = si["category"]
    school.medium = si["medium"]
    school.school_type = si["school_type"]
    school.established_year = si.get("established_year")
    school.affiliation_number = si.get("affiliation_number")
    school.udise_code = udise_code or None

    plan_type = (pi.get("plan_type") or "pilot").strip().lower()
    school.plan_type = plan_type
    school.is_test = bool(pi.get("is_test", False))
    # update status only when not suspended
    if normalize_role(school.status) != "SUSPENDED":
        school.status = "PILOT" if plan_type == "pilot" else "ACTIVE"

    # --- update location/contact ---
    contact.street = lc.get("street_address")
    contact.area = lc.get("area")
    contact.city = lc.get("city")
    contact.district = lc.get("district")
    contact.state = lc.get("state")
    contact.pin_code = lc.get("pincode")
    contact.country = lc.get("country") or "India"
    contact.landmark = lc.get("landmark")
    contact.latitude = lc.get("latitude")
    contact.longitude = lc.get("longitude")
    contact.school_phone = lc.get("school_phone")
    contact.school_email = school_email or None
    contact.website = lc.get("website")

    # --- update management admin ---
    first = ma.get("first_name") or ""
    last = ma.get("last_name") or ""
    mgmt_user.full_name = f"{first} {last}".strip() or mgmt_user.full_name
    mgmt_user.phone = admin_phone
    mgmt_user.email = admin_email or None
    db.add(mgmt_user)

    mgmt_profile.first_name = first
    mgmt_profile.last_name = last
    mgmt_profile.designation = ma.get("designation")
    mgmt_profile.department = ma.get("department")
    mgmt_profile.employee_id = ma.get("employee_id") or mgmt_profile.employee_id
    mgmt_profile.language_preference = ma.get("language")
    mgmt_profile.timezone = ma.get("timezone")

    # --- update academic baseline ---
    academic.current_session = ab.get("current_session")
    start_month = _month_to_int(ab.get("academic_start_month"))
    end_month = _month_to_int(ab.get("academic_end_month"))
    if start_month:
        academic.academic_start_month = start_month
    if end_month:
        academic.academic_end_month = end_month
    academic.working_days_per_week = int(ab.get("working_days_per_week") or academic.working_days_per_week or 6)
    levels = _normalize_class_levels(ab.get("class_levels_enabled") or [])
    academic.class_levels = levels
    academic.lkg_available = "LKG" in levels
    academic.ukg_available = "UKG" in levels
    academic.pre_nursery_available = "Pre Nursery" in levels

    # Ensure school_grades and classes are in sync
    existing_grades = db.query(SchoolGrade).filter(SchoolGrade.school_id == school.id).all()
    grade_by_name = {g.grade_name: g for g in existing_grades}
    selected_names = set()
    for raw in levels:
        grade_name, grade_code, grade_level = _grade_row(raw)
        selected_names.add(grade_name)
        row = grade_by_name.get(grade_name)
        if not row:
            row = SchoolGrade(
                school_id=school.id,
                grade_name=grade_name,
                grade_code=grade_code,
                grade_level=grade_level,
                is_active=True,
            )
        row.is_active = True
        row.grade_code = grade_code
        row.grade_level = grade_level
        db.add(row)

        # Create Class row if missing
        class_exists = (
            db.query(Class.id)
            .filter(Class.school_id == school.id, Class.name == str(raw).strip())
            .first()
        )
        if not class_exists:
            class_public_id = next_public_id(db, tenant_code=school.code, entity="class")
            db.add(Class(school_id=school.id, name=str(raw).strip(), public_id=class_public_id))

    # Deactivate grades removed
    for g in existing_grades:
        if g.grade_name not in selected_names:
            g.is_active = False
            db.add(g)

    # --- modules & limits ---
    modules_dict = ml.get("modules") or {}
    enabled = sorted([k for k, v in modules_dict.items() if bool(v) and k in set(PRD_MODULES)])
    features.modules_enabled = enabled
    limits = ml.get("limits") or {}
    features.max_students = int(limits.get("max_students") or features.max_students or 1000)
    features.max_teachers = int(limits.get("max_teachers") or features.max_teachers or 60)
    features.max_staff = int(limits.get("max_staff") or features.max_staff or 40)
    features.storage_limit_gb = int(limits.get("storage_limit_gb") or features.storage_limit_gb or 100)
    feat_flags = ml.get("features") or {}
    features.api_access = bool(feat_flags.get("api_access") or False)
    features.bulk_operations = bool(feat_flags.get("bulk_operations") or False)
    features.custom_reports = bool(feat_flags.get("custom_reports") or False)

    # Audit
    db.add(AuditLog(user_id=current_user.id, event="SCHOOL_EDITED", identifier=school.public_id))

    db.add(school)
    db.add(contact)
    db.add(academic)
    db.add(features)
    db.add(mgmt_profile)
    db.commit()

    return get_school_detail(db, school_id=str(school.internal_id))
