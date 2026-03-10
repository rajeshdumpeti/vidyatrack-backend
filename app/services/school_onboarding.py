from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.phone import normalize_phone
from app.db.models.idempotency_key import IdempotencyKey
from app.db.models.management_admin import ManagementAdmin
from app.db.models.school import School
from app.db.models.school_academic_details import SchoolAcademicDetails
from app.db.models.school_contact import SchoolContact
from app.db.models.school_features import SchoolFeatures
from app.db.models.school_onboarding_draft import SchoolOnboardingDraft
from app.db.models.user import User
from app.db.models.user_school import UserSchool
from app.db.repositories.school_onboarding import (
    count_schools_created_by,
    find_conflicts,
    normalize_code,
)
from app.services.public_id import next_public_id, derive_tenant_code, ensure_unique_tenant_code

IDEMPOTENCY_SCOPE = "onboarding_phase1"


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
            tenant_code = ensure_unique_tenant_code(
                db,
                derive_tenant_code(payload["school_name"]),
            )
            school_public_id = next_public_id(
                db,
                tenant_code=tenant_code,
                entity="school",
            )
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
                status="ACTIVE",
                public_id=school_public_id,
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

            admin_user = User(
                phone=normalize_phone(payload["admin_phone"]),
                email=payload.get("admin_email"),
                role="MANAGEMENT",
                is_active=True,
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
                employee_id=payload.get("admin_employee_id"),
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

        response_payload = {
            "school": {
                "id": school.id,
                "public_id": school.public_id,
                "name": school.name,
                "code": school.code,
                "status": school.status,
            },
            "management_admin": {
                "id": admin_user.id,
                "public_id": admin_profile.public_id,
                "phone": admin_user.phone,
                "email": admin_user.email,
                "status": "ACTIVE",
            },
            "onboarding": {
                "phase": "phase1",
                "status": "completed",
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
