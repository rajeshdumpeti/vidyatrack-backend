from __future__ import annotations

import hashlib
import json
import re
import secrets
import string
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.phone import normalize_phone
from app.db.models.audit_log import AuditLog
from app.db.models.class_ import Class
from app.db.models.idempotency_key import IdempotencyKey
from app.db.models.management_admin import ManagementAdmin
from app.db.models.school import School
from app.db.models.school_academic_details import SchoolAcademicDetails
from app.db.models.school_contact import SchoolContact
from app.db.models.school_features import SchoolFeatures
from app.db.models.school_grade import SchoolGrade
from app.db.models.school_onboarding_draft import SchoolOnboardingDraft
from app.db.models.user import User
from app.db.models.user_school import UserSchool
from app.db.repositories.school_onboarding import (
    count_schools_created_by,
    find_conflicts,
)
from app.integrations.email.brevo import send_credentials_email
from app.integrations.whatsapp.client import send_credentials_sms
from app.services.public_id import next_public_id, derive_tenant_code, ensure_unique_tenant_code

IDEMPOTENCY_SCOPE = "onboarding_phase1"

_TEMP_PASSWORD_CHARS = string.ascii_uppercase + string.ascii_lowercase + string.digits + "!@#$%"


def _generate_temp_password(length: int = 12) -> str:
    """Generate a secure 12-char temp password with upper, lower, digit, and special char."""
    while True:
        pwd = "".join(secrets.choice(_TEMP_PASSWORD_CHARS) for _ in range(length))
        if (
            any(c.isupper() for c in pwd)
            and any(c.islower() for c in pwd)
            and any(c.isdigit() for c in pwd)
            and any(c in "!@#$%" for c in pwd)
        ):
            return pwd


class OnboardingConflict(Exception):
    def __init__(self, codes: list[str]):
        super().__init__("conflict")
        self.codes = codes


def _hash_payload(payload: dict) -> str:
    payload_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(payload_bytes).hexdigest()


def _enforce_permissions(db: Session, current_user: User) -> None:
    if current_user.role == "super_admin":
        return
    if not current_user.can_create_school:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "INSUFFICIENT_PERMISSIONS", "message": "cannot_create_school"},
        )
    if current_user.max_schools is not None:
        created = count_schools_created_by(db, current_user.id)
        if created >= current_user.max_schools:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "MAX_SCHOOL_LIMIT_REACHED",
                    "message": "max_school_limit_reached",
                },
            )


def validate_phase1_payload(
    db: Session,
    *,
    school_code: str | None,
    udise_code: str | None,
    school_email: str | None,
    admin_phone: str | None,
    admin_email: str | None,
) -> None:
    conflicts = find_conflicts(
        db,
        school_code=school_code,
        udise_code=udise_code,
        school_email=school_email,
        admin_phone=admin_phone,
        admin_email=admin_email,
    )
    if conflicts:
        raise OnboardingConflict(conflicts)


def get_idempotent_response(
    db: Session, *, user_id: int, key: str, request_hash: str
) -> dict | None:
    record = (
        db.query(IdempotencyKey)
        .filter(
            IdempotencyKey.user_id == user_id,
            IdempotencyKey.scope == IDEMPOTENCY_SCOPE,
            IdempotencyKey.key == key,
        )
        .first()
    )
    if not record:
        return None
    if record.request_hash != request_hash:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "IDEMPOTENCY_KEY_REUSE_MISMATCH",
                "message": "idempotency_key_reuse_with_different_payload",
            },
        )
    return {"status": record.response_status, "payload": record.response_json}


def save_idempotent_response(
    db: Session,
    *,
    user_id: int,
    key: str,
    request_hash: str,
    response_json: dict,
    response_status: int,
) -> None:
    record = IdempotencyKey(
        user_id=user_id,
        scope=IDEMPOTENCY_SCOPE,
        key=key,
        request_hash=request_hash,
        response_json=response_json,
        response_status=response_status,
    )
    db.add(record)


def create_phase1_onboarding(
    db: Session,
    *,
    payload: dict,
    current_user: User,
    idempotency_key: str | None,
) -> dict:
    _enforce_permissions(db, current_user)

    # Normalize common identifiers to reduce false "already exists" conflicts.
    # Always store canonical values.
    if payload.get("school_email"):
        payload["school_email"] = str(payload["school_email"]).strip().lower()
    if payload.get("admin_email"):
        payload["admin_email"] = str(payload["admin_email"]).strip().lower()
    if payload.get("udise_code"):
        payload["udise_code"] = str(payload["udise_code"]).strip()

    request_hash = _hash_payload(payload)
    if idempotency_key:
        cached = get_idempotent_response(
            db, user_id=current_user.id, key=idempotency_key, request_hash=request_hash
        )
        if cached:
            return cached

    validate_phase1_payload(
        db,
        school_code=payload.get("school_code"),
        udise_code=payload.get("udise_code"),
        school_email=payload.get("school_email"),
        admin_phone=payload.get("admin_phone"),
        admin_email=payload.get("admin_email"),
    )

    try:
        txn_ctx = db.begin_nested() if db.in_transaction() else db.begin()
        with txn_ctx:
            requested_code = payload.get("school_code")
            base_code = requested_code or derive_tenant_code(payload["school_name"])
            tenant_code = ensure_unique_tenant_code(db, base_code)
            school_public_id = next_public_id(
                db,
                tenant_code=tenant_code,
                entity="school",
            )

            plan_type = (payload.get("plan_type") or "pilot").strip().lower()
            is_test = bool(payload.get("is_test", False))
            trial_days = int(payload.get("trial_days") or 0)
            billing_start_date = payload.get("billing_start_date")
            now = datetime.now(timezone.utc)
            trial_ends_at = None if trial_days <= 0 else (now + timedelta(days=trial_days))
            billing_starts_at = None
            if billing_start_date:
                try:
                    # accepts YYYY-MM-DD
                    billing_starts_at = datetime.fromisoformat(str(billing_start_date)).replace(tzinfo=timezone.utc)
                except Exception:
                    billing_starts_at = None
            school = School(
                name=payload["school_name"].strip(),
                code=tenant_code,
                board=payload["board"],
                category=payload["category"],
                medium=payload["medium"],
                school_type=payload["school_type"],
                established_year=payload["established_year"],
                affiliation_number=payload.get("affiliation_number"),
                udise_code=payload.get("udise_code"),
                status="PILOT" if plan_type == "pilot" else "ACTIVE",
                public_id=school_public_id,
                plan_type=plan_type,
                is_test=is_test,
                trial_ends_at=trial_ends_at if trial_days > 0 else None,
                billing_starts_at=billing_starts_at,
                created_by=current_user.id,
                updated_by=current_user.id,
            )
            db.add(school)
            db.flush()

            contact = SchoolContact(
                school_id=school.id,
                street=payload.get("street"),
                area=payload.get("area"),
                city=payload.get("city"),
                district=payload.get("district"),
                state=payload.get("state"),
                pin_code=payload.get("pin_code"),
                country=payload.get("country"),
                landmark=payload.get("landmark"),
                latitude=payload.get("latitude"),
                longitude=payload.get("longitude"),
                school_phone=payload.get("school_phone"),
                school_email=payload.get("school_email"),
                website=payload.get("website"),
                created_by=current_user.id,
                updated_by=current_user.id,
            )
            db.add(contact)

            academic = SchoolAcademicDetails(
                school_id=school.id,
                current_session=payload.get("current_session"),
                academic_start_month=payload.get("academic_start_month"),
                academic_end_month=payload.get("academic_end_month"),
                working_days_per_week=payload.get("working_days_per_week"),
                class_levels=payload.get("class_levels"),
                lkg_available=payload.get("lkg_available", False),
                ukg_available=payload.get("ukg_available", False),
                pre_nursery_available=payload.get("pre_nursery_available", False),
                created_by=current_user.id,
                updated_by=current_user.id,
            )
            db.add(academic)

            features = SchoolFeatures(
                school_id=school.id,
                modules_enabled=payload.get("modules_enabled"),
                max_students=payload.get("max_students"),
                max_teachers=payload.get("max_teachers"),
                max_staff=payload.get("max_staff"),
                storage_limit_gb=payload.get("storage_limit_gb"),
                api_access=payload.get("api_access", False),
                bulk_operations=payload.get("bulk_operations", False),
                custom_reports=payload.get("custom_reports", False),
                created_by=current_user.id,
                updated_by=current_user.id,
            )
            db.add(features)

            import bcrypt as _bcrypt
            temp_password = _generate_temp_password()
            password_hash = _bcrypt.hashpw(
                temp_password.encode("utf-8"), _bcrypt.gensalt(rounds=12)
            ).decode("utf-8")

            admin_first = payload.get("admin_first_name", "")
            admin_last = payload.get("admin_last_name", "")
            admin_full_name = f"{admin_first} {admin_last}".strip()

            admin_user = User(
                phone=normalize_phone(payload["admin_phone"]),
                email=payload.get("admin_email"),
                role="MANAGEMENT",
                is_active=True,
                full_name=admin_full_name or None,
                password_hash=password_hash,
                is_first_login=True,
            )
            db.add(admin_user)
            db.flush()

            admin_public_id = next_public_id(
                db,
                tenant_code=tenant_code,
                entity="management_admin",
            )
            admin_profile = ManagementAdmin(
                school_id=school.id,
                user_id=admin_user.id,
                public_id=admin_public_id,
                first_name=payload.get("admin_first_name"),
                last_name=payload.get("admin_last_name"),
                designation=payload.get("admin_designation"),
                department=payload.get("admin_department"),
                employee_id=payload.get("admin_employee_id") or f"{tenant_code}-ADM-001",
                language_preference=payload.get("language_preference"),
                timezone=payload.get("timezone"),
                created_by=current_user.id,
                updated_by=current_user.id,
            )
            db.add(admin_profile)

            mapping = UserSchool(
                user_id=admin_user.id,
                school_id=school.id,
                role="MANAGEMENT",
            )
            db.add(mapping)

            # Create Class records for each class_level
            grades_created = 0
            for level_name in payload.get("class_levels", []):
                # PRD school_grades record (separate from Class)
                cleaned = str(level_name).strip()
                if not cleaned:
                    continue
                normalized = cleaned.upper().replace(" ", "_")
                if normalized in {"PRE_NURSERY", "PRE-NURSERY"}:
                    grade_name = "Pre Nursery"
                    grade_code = "PREN"
                    grade_level = -1
                elif normalized == "LKG":
                    grade_name = "LKG"
                    grade_code = "LKG"
                    grade_level = 0
                elif normalized == "UKG":
                    grade_name = "UKG"
                    grade_code = "UKG"
                    grade_level = 1
                elif cleaned.isdigit():
                    grade_name = f"Grade {int(cleaned)}"
                    grade_code = f"GR{int(cleaned)}"
                    grade_level = int(cleaned) + 1
                else:
                    grade_name = cleaned
                    grade_code = re.sub(r"[^A-Za-z0-9]+", "", cleaned.upper())[:10] or "GRD"
                    grade_level = None
                db.add(
                    SchoolGrade(
                        school_id=school.id,
                        grade_name=grade_name,
                        grade_code=grade_code,
                        grade_level=grade_level,
                        is_active=True,
                    )
                )
                class_public_id = next_public_id(
                    db,
                    tenant_code=tenant_code,
                    entity="class",
                )
                db.add(Class(
                    school_id=school.id,
                    name=cleaned,
                    public_id=class_public_id,
                ))
                grades_created += 1

        # --- Post-commit: send credentials & write audit log ---
        admin_phone = admin_user.phone
        admin_email = admin_user.email
        send_via = payload.get("send_credentials_via", "sms")
        admin_name = admin_full_name or admin_first or "Admin"

        sms_delivered = False
        email_delivered = False
        sms_error: str | None = None
        email_error: str | None = None

        if send_via in ("sms", "both"):
            sms_result = send_credentials_sms(
                admin_phone,
                school_name=school.name,
                admin_name=admin_name,
                temp_password=temp_password,
            )
            sms_delivered = sms_result.success
            if not sms_result.success:
                sms_error = sms_result.provider_error_message or "delivery_failed"

        if send_via in ("email", "both"):
            if not admin_email:
                email_delivered = False
                email_error = "ADMIN_EMAIL_MISSING"
            else:
                email_result = send_credentials_email(
                    admin_email,
                    school_name=school.name,
                    admin_name=admin_name,
                    phone=admin_phone,
                    temp_password=temp_password,
                )
                email_delivered = email_result.success
                if not email_result.success:
                    email_error = email_result.provider_error_message or "delivery_failed"

        audit = AuditLog(
            user_id=current_user.id,
            event="SCHOOL_ONBOARDED",
            identifier=school.public_id,
        )
        db.add(audit)
        db.commit()

        response_payload = {
            "school": {
                "id": school.id,
                "internal_id": str(school.internal_id),
                "public_id": school.public_id,
                "name": school.name,
                "code": school.code,
                "status": school.status,
            },
            "management_admin": {
                "id": admin_user.id,
                "internal_id": str(admin_user.internal_id),
                "public_id": admin_profile.public_id,
                "phone": admin_user.phone,
                "email": admin_user.email,
                "status": "ACTIVE",
            },
            "onboarding": {
                "phase": "phase1",
                "status": "completed",
                "grades_created": grades_created,
                "sms_delivered": sms_delivered,
                "email_delivered": email_delivered,
                "sms_error": sms_error,
                "email_error": email_error,
                "temp_password": temp_password,
                "next_actions": [
                    "upload_documents",
                    "setup_subscription",
                    "invite_staff",
                ],
            },
        }

        if idempotency_key:
            save_idempotent_response(
                db,
                user_id=current_user.id,
                key=idempotency_key,
                request_hash=request_hash,
                response_json=response_payload,
                response_status=status.HTTP_201_CREATED,
            )
            db.commit()

        return {"status": status.HTTP_201_CREATED, "payload": response_payload}

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "DUPLICATE_RESOURCE", "message": "unique_conflict"},
        )


def create_draft(db: Session, *, payload: dict, current_user: User) -> SchoolOnboardingDraft:
    draft = SchoolOnboardingDraft(
        id=str(uuid.uuid4()),
        payload=payload,
        status="draft",
        created_by=current_user.id,
        updated_by=current_user.id,
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)
    return draft


def update_draft(
    db: Session, *, draft_id: str, payload: dict, current_user: User
) -> SchoolOnboardingDraft:
    draft = db.query(SchoolOnboardingDraft).filter(
        SchoolOnboardingDraft.id == draft_id
    ).first()
    if not draft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "DRAFT_NOT_FOUND", "message": "draft_not_found"},
        )
    draft.payload = payload
    draft.updated_by = current_user.id
    draft.updated_at = datetime.now(timezone.utc)
    db.add(draft)
    db.commit()
    db.refresh(draft)
    return draft


def get_draft(db: Session, *, draft_id: str) -> SchoolOnboardingDraft:
    draft = db.query(SchoolOnboardingDraft).filter(
        SchoolOnboardingDraft.id == draft_id
    ).first()
    if not draft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "DRAFT_NOT_FOUND", "message": "draft_not_found"},
        )
    return draft
