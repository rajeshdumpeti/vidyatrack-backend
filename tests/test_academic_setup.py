from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1.deps import get_current_user, get_db, get_valid_school_id
from app.db.models.class_ import Class
from app.db.models.section import Section
from app.db.models.subject import Subject
from app.db.models.user import User
from app.main import app


def test_get_academic_setup_returns_classes_sections_subjects():
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    User.__table__.create(bind=engine)
    Class.__table__.create(bind=engine)
    Section.__table__.create(bind=engine)
    Subject.__table__.create(bind=engine)

    db = SessionLocal()
    try:
        db.add_all(
            [
                Class(id=1, public_id="CLS000000000000000000000000001", school_id=18, name="grade 10th"),
                Class(id=2, public_id="CLS000000000000000000000000002", school_id=18, name="grade 9th"),
                Section(id=30, public_id="SEC000000000000000000000000030", school_id=18, class_id=1, name="A"),
                Section(id=31, public_id="SEC000000000000000000000000031", school_id=18, class_id=1, name="B"),
                Subject(id=11, public_id="SUB000000000000000000000000011", school_id=18, name="maths"),
                Subject(id=12, public_id="SUB000000000000000000000000012", school_id=18, name="english"),
            ]
        )
        db.commit()
    finally:
        db.close()

    def _override_get_db():
        test_db = SessionLocal()
        try:
            yield test_db
        finally:
            test_db.close()

    def _override_get_current_user():
        return User(
            id=500,
            phone="+16190000001",
            email="mgmt@example.com",
            role="MANAGEMENT",
            is_active=True,
            can_create_school=False,
            max_schools=None,
        )

    def _override_get_valid_school_id():
        return 18

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user
    app.dependency_overrides[get_valid_school_id] = _override_get_valid_school_id

    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/academic-setup?school_id=18")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["school_id"] == 18
    assert len(body["classes"]) == 2
    assert len(body["sections"]) == 2
    assert len(body["subjects"]) == 2
    assert body["sections"][0]["class_name"] == "grade 10th"
