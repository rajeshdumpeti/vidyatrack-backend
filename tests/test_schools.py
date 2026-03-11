import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1.deps import get_current_user, get_db
from app.db.base import Base
from app.db.models.public_id_counter import PublicIdCounter
from app.db.models.school import School
from app.db.models.user import User
from app.db.models.user_school import UserSchool
from app.main import app


@pytest.fixture()
def schools_client():
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
            PublicIdCounter.__table__,
            UserSchool.__table__,
        ],
    )

    db = TestingSessionLocal()
    db.add_all(
        [
            School(id=18, public_id="SCH000000000000000000000000018", name="Alpha School"),
            School(id=19, public_id="SCH000000000000000000000000019", name="Beta School"),
            User(
                id=1,
                phone="+910000000001",
                email="super@example.com",
                role="SUPER_ADMIN",
                is_active=True,
                can_create_school=True,
            ),
            User(
                id=2,
                phone="+910000000002",
                email="manager@example.com",
                role="MANAGEMENT",
                is_active=True,
                can_create_school=False,
            ),
        ]
    )
    db.add_all(
        [
            UserSchool(user_id=2, school_id=18, role="management"),
            UserSchool(user_id=1, school_id=18, role="teacher"),
            UserSchool(user_id=1, school_id=19, role="student"),
        ]
    )
    db.commit()

    def _override_get_db():
        yield db

    def _override_get_current_user():
        return db.get(User, 1)

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user

    with TestClient(app) as client:
        yield client, db

    db.close()
    app.dependency_overrides.clear()


def test_list_schools_includes_role_counts(schools_client):
    client, _ = schools_client

    response = client.get("/api/v1/schools")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    assert body[0]["teacher_count"] == 1
    assert body[0]["student_count"] == 0
    assert body[1]["teacher_count"] == 0
    assert body[1]["student_count"] == 1


def test_create_school_as_super_admin(schools_client):
    client, db = schools_client

    response = client.post(
        "/api/v1/schools",
        json={
            "name": "Gamma School",
            "school_code": "GAMMA",
            "admin_phone": "+910000000099",
            "admin_email": "gamma-admin@example.com",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Gamma School"
    assert body["public_id"]
    assert db.query(School).count() == 3
    assert db.query(UserSchool).filter(UserSchool.school_id == body["id"]).count() == 1
