from app.db.models.management_admin import ManagementAdmin
from app.db.models.school import School
from app.db.models.school_academic_details import SchoolAcademicDetails
from app.db.models.school_contact import SchoolContact
from app.db.models.school_features import SchoolFeatures
from app.db.models.user import User
from app.db.models.user_school import UserSchool


def _payload():
    return {
        "school_name": "Green Valley School",
        "school_code": "GVS-001",
        "board": "CBSE",
        "category": "PRIVATE",
        "medium": "ENGLISH",
        "school_type": "CO_ED",
        "established_year": 2005,
        "affiliation_number": "AFF-123",
        "udise_code": "12345678901",
        "street": "Main Street",
        "area": "Central",
        "city": "Bengaluru",
        "district": "Bengaluru",
        "state": "Karnataka",
        "pin_code": "560001",
        "country": "India",
        "landmark": "Near Park",
        "school_phone": "+91 9988776655",
        "school_email": "info@greenv.edu",
        "website": "https://greenv.edu",
        "admin_first_name": "Asha",
        "admin_last_name": "Rao",
        "admin_designation": "Administrator",
        "admin_department": "Operations",
        "admin_employee_id": "ADM-01",
        "admin_phone": "+91 9876543210",
        "admin_email": "asha@greenv.edu",
        "language_preference": "en",
        "timezone": "Asia/Kolkata",
        "current_session": "2025-2026",
        "academic_start_month": 6,
        "academic_end_month": 3,
        "working_days_per_week": 5,
        "class_levels": ["1", "2"],
        "lkg_available": True,
        "ukg_available": True,
        "pre_nursery_available": False,
        "modules_enabled": ["attendance", "fees"],
        "max_students": 1200,
        "max_teachers": 80,
        "max_staff": 40,
        "storage_limit_gb": 100,
        "api_access": True,
        "bulk_operations": True,
        "custom_reports": False,
    }


def test_submit_phase1_success(client, db_session):
    resp = client.post("/api/v1/platform/schools/onboarding/phase1", json=_payload())
    assert resp.status_code == 201
    body = resp.json()
    assert body["school"]["name"] == "Green Valley School"
    assert body["management_admin"]["email"] == "asha@greenv.edu"

    assert db_session.query(School).count() == 1
    assert db_session.query(SchoolContact).count() == 1
    assert db_session.query(SchoolAcademicDetails).count() == 1
    assert db_session.query(SchoolFeatures).count() == 1
    assert db_session.query(User).count() == 2  # super admin + management admin
    assert db_session.query(UserSchool).count() == 1
    assert db_session.query(ManagementAdmin).count() == 1


def test_submit_phase1_conflict_admin_phone(client, db_session):
    existing = User(phone="+919876543210", email="old@school.com", role="MANAGEMENT", is_active=True)
    db_session.add(existing)
    db_session.commit()

    resp = client.post("/api/v1/platform/schools/onboarding/phase1", json=_payload())
    assert resp.status_code == 409
    assert "ADMIN_PHONE_ALREADY_EXISTS" in resp.json()["detail"]["conflicts"]
    assert db_session.query(School).count() == 0


def test_idempotency_key_reuse(client, db_session):
    payload = _payload()
    headers = {"Idempotency-Key": "phase1-key"}

    first = client.post(
        "/api/v1/platform/schools/onboarding/phase1", json=payload, headers=headers
    )
    assert first.status_code == 201

    second = client.post(
        "/api/v1/platform/schools/onboarding/phase1", json=payload, headers=headers
    )
    assert second.status_code == 201
    assert second.json() == first.json()

    payload["school_code"] = "GVS-002"
    third = client.post(
        "/api/v1/platform/schools/onboarding/phase1", json=payload, headers=headers
    )
    assert third.status_code == 409
    assert third.json()["detail"]["code"] == "IDEMPOTENCY_KEY_REUSE_MISMATCH"


def test_validate_phase1_reports_conflicts(client, db_session):
    db_session.add(
        User(
            phone="+919876543210",
            email="asha@greenv.edu",
            role="MANAGEMENT",
            is_active=True,
        )
    )
    db_session.commit()

    resp = client.post(
        "/api/v1/platform/schools/onboarding/phase1/validate",
        json={
            "school_code": "GVS-001",
            "admin_phone": "+91 9876543210",
            "admin_email": "asha@greenv.edu",
        },
    )

    assert resp.status_code == 409
    conflicts = resp.json()["detail"]["conflicts"]
    assert "ADMIN_PHONE_ALREADY_EXISTS" in conflicts
    assert "ADMIN_EMAIL_ALREADY_EXISTS" in conflicts


def test_phase1_draft_lifecycle(client):
    create_resp = client.post(
        "/api/v1/platform/schools/onboarding/phase1/draft",
        json={"payload": {"school_name": "Draft School", "step": 1}},
    )
    assert create_resp.status_code == 201
    created = create_resp.json()
    assert created["status"] == "draft"
    assert created["payload"]["school_name"] == "Draft School"

    draft_id = created["id"]
    update_resp = client.patch(
        f"/api/v1/platform/schools/onboarding/phase1/{draft_id}",
        json={"payload": {"school_name": "Draft School Updated", "step": 2}},
    )
    assert update_resp.status_code == 200
    updated = update_resp.json()
    assert updated["payload"]["school_name"] == "Draft School Updated"
    assert updated["payload"]["step"] == 2

    get_resp = client.get(f"/api/v1/platform/schools/onboarding/phase1/{draft_id}")
    assert get_resp.status_code == 200
    fetched = get_resp.json()
    assert fetched["id"] == draft_id
    assert fetched["payload"]["school_name"] == "Draft School Updated"
