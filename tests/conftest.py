import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1.deps import get_current_user, get_db
from app.db.base import Base
from app.db.models.idempotency_key import IdempotencyKey
from app.db.models.management_admin import ManagementAdmin
from app.db.models.public_id_counter import PublicIdCounter
from app.db.models.audit_log import AuditLog
from app.db.models.school import School
from app.db.models.school_academic_details import SchoolAcademicDetails
from app.db.models.school_contact import SchoolContact
from app.db.models.school_features import SchoolFeatures
from app.db.models.school_grade import SchoolGrade
from app.db.models.class_ import Class
from app.db.models.student import Student
from app.db.models.school_onboarding_draft import SchoolOnboardingDraft
from app.db.models.user import User
from app.db.models.user_school import UserSchool
from app.main import app


@pytest.fixture()
def db_session():
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
            SchoolContact.__table__,
            SchoolAcademicDetails.__table__,
            SchoolFeatures.__table__,
            SchoolGrade.__table__,
            Class.__table__,
            ManagementAdmin.__table__,
            SchoolOnboardingDraft.__table__,
            IdempotencyKey.__table__,
            PublicIdCounter.__table__,
            AuditLog.__table__,
            Student.__table__,
        ],
    )

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def current_user(db_session):
    user = User(
        phone="9999999999",
        email="super@example.com",
        role="SUPER_ADMIN",
        is_active=True,
        can_create_school=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture()
def client(db_session, current_user):
    def _override_get_db():
        yield db_session

    def _override_get_current_user():
        return current_user

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
