from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db.models.user import User
from app.services.school_onboarding import OnboardingConflict, create_phase1_onboarding


_MONTHS: dict[str, int] = {
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


def _month_to_int(value: str) -> int:
    key = (value or "").strip().lower()
    if key not in _MONTHS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "INVALID_MONTH", "value": value},
        )
    return _MONTHS[key]


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
    # dedupe while keeping order
    seen: set[str] = set()
    deduped: list[str] = []
    for item in out:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return deduped


def _modules_enabled(modules: dict[str, bool]) -> list[str]:
    enabled = [k for k, v in (modules or {}).items() if bool(v)]
    enabled.sort()
    return enabled


def create_school_from_prd_payload(
    db: Session,
    *,
    payload: dict[str, Any],
    current_user: User,
    idempotency_key: str | None,
) -> dict[str, Any]:
    """
    PRD API: POST /api/v1/superadmin/schools/create

    Accepts nested payload and maps into the existing onboarding phase1 service.
    Returns a PRD-shaped success envelope.
    """
    si = payload["school_identity"]
    lc = payload["location_contact"]
    ma = payload["management_admin"]
    ab = payload["academic_baseline"]
    ml = payload["modules_limits"]
    pi = payload["plan_info"]

    flat: dict[str, Any] = {
        # identity
        "school_name": si["school_name"],
        "school_code": si.get("school_code"),
        "board": si["board"],
        "category": si["category"],
        "medium": si["medium"],
        "school_type": si["school_type"],
        "established_year": si.get("established_year"),
        "affiliation_number": si.get("affiliation_number"),
        "udise_code": si.get("udise_code"),
        # location
        "street": lc["street_address"],
        "area": lc.get("area"),
        "city": lc["city"],
        "district": lc["district"],
        "state": lc["state"],
        "pin_code": lc["pincode"],
        "country": lc.get("country") or "India",
        "landmark": lc.get("landmark"),
        "latitude": lc.get("latitude"),
        "longitude": lc.get("longitude"),
        "school_phone": lc["school_phone"],
        "school_email": lc["school_email"],
        "website": lc.get("website"),
        # management admin
        "admin_first_name": ma["first_name"],
        "admin_last_name": ma["last_name"],
        "admin_designation": ma.get("designation"),
        "admin_department": ma.get("department"),
        "admin_employee_id": ma.get("employee_id"),
        "admin_phone": ma["phone"],
        "admin_email": ma["email"],
        "send_credentials_via": ma.get("send_credentials_via", "sms"),
        "language_preference": ma.get("language", "en"),
        "timezone": ma.get("timezone", "Asia/Kolkata"),
        # academic baseline
        "current_session": ab["current_session"],
        "academic_start_month": _month_to_int(ab["academic_start_month"]),
        "academic_end_month": _month_to_int(ab["academic_end_month"]),
        "working_days_per_week": int(ab["working_days_per_week"]),
        "class_levels": _normalize_class_levels(ab["class_levels_enabled"]),
        "lkg_available": "LKG" in _normalize_class_levels(ab["class_levels_enabled"]),
        "ukg_available": "UKG" in _normalize_class_levels(ab["class_levels_enabled"]),
        "pre_nursery_available": "Pre Nursery" in _normalize_class_levels(ab["class_levels_enabled"]),
        # modules/limits/features
        "modules_enabled": _modules_enabled(ml.get("modules") or {}),
        "max_students": int((ml.get("limits") or {}).get("max_students") or 1000),
        "max_teachers": int((ml.get("limits") or {}).get("max_teachers") or 60),
        "max_staff": int((ml.get("limits") or {}).get("max_staff") or 40),
        "storage_limit_gb": int((ml.get("limits") or {}).get("storage_limit_gb") or 100),
        "api_access": bool((ml.get("features") or {}).get("api_access") or False),
        "bulk_operations": bool((ml.get("features") or {}).get("bulk_operations") or False),
        "custom_reports": bool((ml.get("features") or {}).get("custom_reports") or False),
        # plan info
        "plan_type": pi.get("plan_type", "pilot"),
        "is_test": bool(pi.get("is_test", False)),
        "trial_days": int(pi.get("trial_days") or 0),
        "billing_start_date": (
            pi.get("billing_start_date").isoformat()
            if isinstance(pi.get("billing_start_date"), date)
            else pi.get("billing_start_date")
        ),
    }

    # `create_phase1_onboarding` expects a dict and handles conflicts/idempotency.
    try:
        result = create_phase1_onboarding(
            db,
            payload=flat,
            current_user=current_user,
            idempotency_key=idempotency_key,
        )
    except OnboardingConflict as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "CONFLICT", "conflicts": exc.codes},
        ) from exc

    payload_out = result["payload"]
    school = payload_out["school"]
    mgmt = payload_out["management_admin"]
    onboarding = payload_out["onboarding"]

    def _grade_name(level: str) -> str:
        cleaned = str(level).strip()
        key = cleaned.lower().replace("-", "_").replace(" ", "_")
        if key == "pre_nursery":
            return "Pre Nursery"
        if key == "lkg":
            return "LKG"
        if key == "ukg":
            return "UKG"
        if cleaned.isdigit():
            return f"Grade {int(cleaned)}"
        return cleaned or "Grade"

    grade_names = [_grade_name(x) for x in flat.get("class_levels", [])]

    return {
        "success": True,
        "data": {
            "school_id": school.get("internal_id"),
            "vt_school_id": school.get("public_id"),
            "school_name": school.get("name"),
            "grades_created": grade_names,
            "management_admin": {
                "user_id": mgmt.get("internal_id"),
                "full_name": f"{flat['admin_first_name']} {flat['admin_last_name']}".strip(),
                "login_phone": mgmt.get("phone"),
                "login_email": mgmt.get("email"),
                "sms_delivered": bool(onboarding.get("sms_delivered")),
                "email_delivered": bool(onboarding.get("email_delivered")),
                "sms_error": onboarding.get("sms_error"),
                "email_error": onboarding.get("email_error"),
                "is_first_login": True,
            },
            "setup_next_steps": [
                "Management Admin will receive login credentials",
                "Management must add sections to each grade (A, B, C)",
                "Management must add subjects per grade",
                "Management must set fee structure",
                "Management must register teachers and enroll students",
            ],
        },
    }
