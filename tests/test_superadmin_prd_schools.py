from app.db.models.school import School
from app.db.models.school_grade import SchoolGrade
from app.db.models.school_features import SchoolFeatures


def _prd_payload():
    return {
        "school_identity": {
            "school_name": "PRD Test School",
            "school_code": None,
            "board": "cbse",
            "category": "primary",
            "medium": "english",
            "school_type": "co_educational",
            "established_year": 2002,
            "affiliation_number": None,
            "udise_code": None,
        },
        "location_contact": {
            "street_address": "7-6-6 Vidyanagar",
            "area": None,
            "city": "Karimnagar",
            "district": "Karim Nagar",
            "state": "Telangana",
            "pincode": "505327",
            "country": "India",
            "landmark": None,
            "latitude": None,
            "longitude": None,
            "school_phone": "+919876543210",
            "school_email": "contact@prdtest.edu",
            "website": None,
        },
        "management_admin": {
            "first_name": "Rajesh",
            "last_name": "Admin",
            "designation": "Director",
            "department": "CEO",
            "employee_id": None,
            "phone": "+919999999999",
            "email": "admin@prdtest.edu",
            "language": "en",
            "timezone": "Asia/Kolkata",
            "send_credentials_via": "email",
        },
        "academic_baseline": {
            "current_session": "2026-2027",
            "academic_start_month": "april",
            "academic_end_month": "march",
            "working_days_per_week": 6,
            "class_levels_enabled": ["lkg", "ukg", "1", "2"],
        },
        "modules_limits": {
            "modules": {
                "attendance": True,
                "exams": True,
                "fees": False,
                "communication": True,
                "reports": True,
            },
            "limits": {"max_students": 1000, "max_teachers": 60, "max_staff": 40, "storage_limit_gb": 100},
            "features": {"api_access": False, "bulk_operations": True, "custom_reports": False},
        },
        "plan_info": {"plan_type": "pilot", "is_test": False, "trial_days": 0, "billing_start_date": None},
    }


def test_prd_create_school_success(client, db_session):
    resp = client.post("/api/v1/superadmin/schools/create", json=_prd_payload())
    assert resp.status_code == 201
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["vt_school_id"]
    assert body["data"]["management_admin"]["login_email"] == "admin@prdtest.edu"

    # school + grades created
    assert db_session.query(School).count() == 1
    assert db_session.query(SchoolGrade).count() >= 1


def test_prd_school_detail_endpoint(client):
    create = client.post("/api/v1/superadmin/schools/create", json=_prd_payload())
    school_id = create.json()["data"]["school_id"]

    detail = client.get(f"/api/v1/superadmin/schools/{school_id}")
    assert detail.status_code == 200
    payload = detail.json()
    assert payload["success"] is True
    assert payload["data"]["school"]["id"] == school_id
    assert payload["data"]["school"]["plan_type"] == "pilot"


def test_prd_mark_test_flag(client, db_session):
    create = client.post("/api/v1/superadmin/schools/create", json=_prd_payload())
    school_id = create.json()["data"]["school_id"]

    patch = client.patch(f"/api/v1/superadmin/schools/{school_id}", json={"is_test": True})
    assert patch.status_code == 200
    assert patch.json()["data"]["is_test"] is True

    school = db_session.query(School).first()
    assert school is not None
    assert school.is_test is True


def test_module_gating_blocks_attendance_when_disabled(client, db_session):
    create = client.post("/api/v1/superadmin/schools/create", json=_prd_payload())
    assert create.status_code == 201

    school = db_session.query(School).first()
    assert school is not None

    features = db_session.query(SchoolFeatures).filter(SchoolFeatures.school_id == school.id).first()
    assert features is not None
    # Disable attendance module
    features.modules_enabled = ["communication"]
    db_session.add(features)
    db_session.commit()

    blocked = client.get(f"/api/v1/attendance?date=2026-04-04&school_id={school.id}")
    assert blocked.status_code == 403
    assert blocked.json()["detail"]["code"] == "MODULE_NOT_ENABLED"
    assert blocked.json()["detail"]["module"] == "attendance"


def test_suspend_and_reactivate_school(client):
    create = client.post("/api/v1/superadmin/schools/create", json=_prd_payload())
    school_id = create.json()["data"]["school_id"]

    suspend = client.post(
        f"/api/v1/superadmin/schools/{school_id}/suspend",
        json={"reason": "Payment overdue", "notify_management": False},
    )
    assert suspend.status_code == 200
    assert suspend.json()["data"]["status"] == "suspended"

    reactivate = client.post(
        f"/api/v1/superadmin/schools/{school_id}/reactivate",
        json={"notify_management": False},
    )
    assert reactivate.status_code == 200
    assert reactivate.json()["data"]["status"] in {"pilot", "active"}


def test_reset_management_password_returns_temp_password(client):
    create = client.post("/api/v1/superadmin/schools/create", json=_prd_payload())
    school_id = create.json()["data"]["school_id"]
    mgmt_user_id = create.json()["data"]["management_admin"]["user_id"]

    reset = client.post(
        f"/api/v1/superadmin/schools/{school_id}/reset-management-password",
        json={"user_id": mgmt_user_id, "send_via": "email", "reason": "test"},
    )
    assert reset.status_code == 200
    assert reset.json()["success"] is True
    assert isinstance(reset.json()["data"]["temporary_password"], str)
    assert len(reset.json()["data"]["temporary_password"]) >= 12
