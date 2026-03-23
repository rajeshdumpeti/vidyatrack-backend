import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1.deps import get_current_user, get_db
from app.db.base import Base
from app.db.models.management_admin import ManagementAdmin
from app.db.models.principal import Principal
from app.db.models.school import School
from app.db.models.student import Student
from app.db.models.teacher import Teacher
from app.db.models.user import User
from app.db.models.user_school import UserSchool
from app.main import app


@pytest.fixture()
def dashboard_client():
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    Base.metadata.create_all(
        bind=engine,
        tables=[
            User.__table__,
            School.__table__,
            UserSchool.__table__,
            Teacher.__table__,
            Student.__table__,
            Principal.__table__,
            ManagementAdmin.__table__,
        ],
    )

    db = TestingSessionLocal()
    school = School(public_id="SCH000000000000000000000000001", name="Pilot School")
    db.add(school)
    db.flush()

    super_admin = User(
        phone="+910000000001",
        email="sa@example.com",
        role="super_admin",
        is_active=True,
        can_create_school=True,
    )
    teacher_user = User(
        phone="+910000000002",
        email="teacher@example.com",
        role="teacher",
        is_active=True,
    )
    management_user = User(
        phone="+910000000003",
        email="manager@example.com",
        role="management",
        is_active=True,
    )
    db.add_all([super_admin, teacher_user, management_user])
    db.flush()

    db.add_all(
        [
            UserSchool(user_id=teacher_user.id, school_id=school.id, role="teacher"),
            UserSchool(user_id=management_user.id, school_id=school.id, role="management"),
            Teacher(
                public_id="TCH000000000000000000000000001",
                school_id=school.id,
                user_id=teacher_user.id,
                name="Teacher One",
                email="teacher@example.com",
            ),
            Student(
                public_id="STD000000000000000000000000001",
                school_id=school.id,
                section_id=None,
                first_name=None,
                last_name=None,
                name="Student One",
                date_of_birth=None,
                gender=None,
                roll_number=None,
                admission_date=None,
                parent_phone="+910000009999",
                parent_name="Parent One",
            ),
        ]
    )
    db.commit()

    def _override_get_db():
        yield db

    def _override_get_current_user():
        return super_admin

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user

    with TestClient(app) as client:
        yield client, school.id, management_user

    db.close()
    app.dependency_overrides.clear()


def test_school_dashboard_counts_and_lists(dashboard_client):
    client, school_id, _ = dashboard_client

    dashboard = client.get(f"/api/v1/schools/{school_id}/dashboard")
    assert dashboard.status_code == 200
    assert dashboard.json() == {
        "school_id": school_id,
        "school_public_id": "SCH000000000000000000000000001",
        "teacher_count": 1,
        "student_count": 1,
        "staff_count": 1,
        "total_registered": 3,
    }

    teachers = client.get(f"/api/v1/schools/{school_id}/teachers")
    assert teachers.status_code == 200
    assert len(teachers.json()["data"]) == 1
    assert teachers.json()["data"][0]["name"] == "Teacher One"

    students = client.get(f"/api/v1/schools/{school_id}/students")
    assert students.status_code == 200
    assert len(students.json()["data"]) == 1
    assert students.json()["data"][0]["name"] == "Student One"

    staff = client.get(f"/api/v1/schools/{school_id}/staff")
    assert staff.status_code == 200
    assert len(staff.json()["data"]) == 1
    assert staff.json()["data"][0]["role"] == "management"


def test_school_dashboard_requires_super_admin(dashboard_client):
    client, school_id, management_user = dashboard_client

    def _override_get_current_user():
        return management_user

    app.dependency_overrides[get_current_user] = _override_get_current_user

    response = client.get(f"/api/v1/schools/{school_id}/dashboard")
    assert response.status_code == 403
    assert response.json()["detail"] == "insufficient_permissions"


def test_school_dashboard_not_found(dashboard_client):
    client, _, _ = dashboard_client

    response = client.get("/api/v1/schools/9999/dashboard")

    assert response.status_code == 404
    assert response.json()["detail"] == "school_not_found"
