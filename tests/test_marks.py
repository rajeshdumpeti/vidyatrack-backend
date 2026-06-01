from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1.deps import get_current_user, get_db
from app.db.base import Base
from app.db.models.attendance_submission import AttendanceSubmission
from app.db.models.class_ import Class
from app.db.models.marks_record import MarksRecord
from app.db.models.marks_submission import MarksSubmission
from app.db.models.notification_outbox import NotificationOutbox
from app.db.models.school import School
from app.db.models.school_features import SchoolFeatures
from app.db.models.section import Section
from app.db.models.student import Student
from app.db.models.subject import Subject
from app.db.models.user import User
from app.db.models.user_school import UserSchool
from app.main import app


def _build_client():
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
            SchoolFeatures.__table__,
            Class.__table__,
            Section.__table__,
            Subject.__table__,
            Student.__table__,
            MarksRecord.__table__,
            MarksSubmission.__table__,
            AttendanceSubmission.__table__,
            NotificationOutbox.__table__,
        ],
    )

    db = TestingSessionLocal()
    db.add(
        School(
            id=18,
            public_id="SCH000000000000000000000000018",
            name="Marks School",
        )
    )
    db.add(
        User(
            id=500,
            phone="+16190000001",
            email="teacher@example.com",
            role="TEACHER",
            is_active=True,
        )
    )
    db.add(
        UserSchool(
            user_id=500,
            school_id=18,
            role="TEACHER",
            is_active=True,
        )
    )
    db.add(
        Class(
            id=1,
            public_id="CLS000000000000000000000000001",
            school_id=18,
            name="Grade 6th",
        )
    )
    db.add(
        Section(
            id=1,
            public_id="SEC000000000000000000000000001",
            school_id=18,
            class_id=1,
            name="A",
        )
    )
    db.add(
        Subject(
            id=11,
            public_id="SUB000000000000000000000000011",
            school_id=18,
            name="Maths",
        )
    )
    db.add_all(
        [
            Student(
                id=101,
                public_id="STD000000000000000000000000101",
                school_id=18,
                section_id=1,
                name="Rahul Sharma",
                parent_phone="+919999000001",
                parent_name="Parent Rahul",
            ),
            Student(
                id=102,
                public_id="STD000000000000000000000000102",
                school_id=18,
                section_id=1,
                name="Ananya Verma",
                parent_phone="+919999000002",
                parent_name="Parent Ananya",
            ),
        ]
    )
    db.commit()

    def _override_get_db():
        yield db

    def _override_get_current_user():
        return db.get(User, 500)

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user

    return db


def test_marks_record_submit_and_list_happy_path():
    db = _build_client()
    try:
        with TestClient(app) as client:
            record_resp = client.post(
                "/api/v1/marks/record?school_id=18",
                json={
                    "student_id": 101,
                    "subject_id": 11,
                    "exam_type": "mid term",
                    "marks_obtained": 42,
                    "max_marks": 50,
                },
            )
            assert record_resp.status_code == 201
            record_body = record_resp.json()
            assert record_body["exam_type"] == "MID_TERM"
            assert record_body["marks_obtained"] == 42

            submit_resp = client.post(
                "/api/v1/marks/submit?school_id=18",
                json={"section_id": 1, "subject_id": 11, "exam_type": "mid term"},
            )
            assert submit_resp.status_code == 201
            submit_body = submit_resp.json()
            assert submit_body["exam_type"] == "MID_TERM"
            assert submit_body["status"] == "submitted"

            list_resp = client.get(
                "/api/v1/marks",
                params={
                    "school_id": 18,
                    "section_id": 1,
                    "subject_id": 11,
                    "exam_type": "mid term",
                },
            )
            assert list_resp.status_code == 200
            list_body = list_resp.json()
            assert len(list_body) == 1
            assert list_body[0]["student_name"] == "Rahul Sharma"
            assert list_body[0]["class_name"] == "Grade 6th"
            assert list_body[0]["section_name"] == "A"
            assert db.query(NotificationOutbox).count() == 2
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_marks_record_rejects_invalid_section_on_list():
    db = _build_client()
    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/marks",
                params={
                    "school_id": 18,
                    "section_id": 999,
                    "subject_id": 11,
                    "exam_type": "final exam",
                },
            )
            assert response.status_code == 400
            assert response.json()["detail"] == "invalid_section_id"
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_marks_record_returns_200_on_idempotent_update():
    db = _build_client()
    try:
        with TestClient(app) as client:
            payload = {
                "student_id": 101,
                "subject_id": 11,
                "exam_type": "unit test",
                "marks_obtained": 18,
                "max_marks": 20,
            }
            first = client.post("/api/v1/marks/record?school_id=18", json=payload)
            assert first.status_code == 201

            second = client.post("/api/v1/marks/record?school_id=18", json=payload)
            assert second.status_code == 200
            assert second.json()["marks_obtained"] == 18
    finally:
        app.dependency_overrides.clear()
        db.close()
