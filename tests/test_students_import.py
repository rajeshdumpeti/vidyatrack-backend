from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1.deps import get_current_user, get_db, get_valid_school_id
from app.db.models.class_ import Class
from app.db.models.public_id_counter import PublicIdCounter
from app.db.models.school import School
from app.db.models.section import Section
from app.db.models.student import Student
from app.db.models.student_import_batch import StudentImportBatch
from app.db.models.user import User
from app.main import app


def _setup_test_app():
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    School.__table__.create(bind=engine)
    User.__table__.create(bind=engine)
    Class.__table__.create(bind=engine)
    Section.__table__.create(bind=engine)
    Student.__table__.create(bind=engine)
    StudentImportBatch.__table__.create(bind=engine)
    PublicIdCounter.__table__.create(bind=engine)

    db = SessionLocal()
    try:
        db.add(
            School(
                id=18,
                public_id="SCH000000000000000000000000018",
                name="Vidyatrack Public School",
            )
        )
        db.add(
            User(
                id=500,
                phone="+16190000001",
                email="mgmt@example.com",
                role="MANAGEMENT",
                is_active=True,
                can_create_school=False,
                max_schools=None,
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

    return SessionLocal


def test_students_import_preview_and_commit_happy_path():
    SessionLocal = _setup_test_app()
    try:
        with TestClient(app) as client:
            csv_content = (
                "first_name,last_name,parent_phone,class_name,section_name,roll_number,date_of_birth\n"
                "Rahul,Sharma,9876511111,Grade 6th,A,101,2012-04-10\n"
                "Ananya,Verma,9876522222,Grade 6th,A,102,2012-08-21\n"
            )

            preview = client.post(
                "/api/v1/students/import/preview?school_id=18",
                files={"file": ("students.csv", csv_content, "text/csv")},
            )
            assert preview.status_code == 200
            body = preview.json()
            assert body["valid_rows"] == 2
            assert body["invalid_rows"] == 0
            assert body["duplicate_rows"] == 0
            assert body["import_token"] is not None

            commit = client.post(
                "/api/v1/students/import/commit?school_id=18",
                json={"import_token": body["import_token"], "mode": "skip_duplicates"},
            )
            assert commit.status_code == 200
            commit_body = commit.json()
            assert commit_body["created_rows"] == 2
            assert commit_body["duplicate_rows"] == 0
            assert commit_body["failed_rows"] == 0

            db = SessionLocal()
            try:
                students_count = db.query(Student).count()
                assert students_count == 2
            finally:
                db.close()
    finally:
        app.dependency_overrides.clear()


def test_students_import_preview_marks_invalid_rows():
    _setup_test_app()
    try:
        with TestClient(app) as client:
            csv_content = (
                "name,parent_phone,class_name,section_name,date_of_birth\n"
                "Only Name,123,Grade 6th,A,10-04-2012\n"
            )

            preview = client.post(
                "/api/v1/students/import/preview?school_id=18",
                files={"file": ("students.csv", csv_content, "text/csv")},
            )
            assert preview.status_code == 200
            body = preview.json()
            assert body["valid_rows"] == 0
            assert body["invalid_rows"] == 1
            assert body["import_token"] is None
            assert "date_of_birth_must_be_yyyy_mm_dd" in body["rows"][0]["errors"]
    finally:
        app.dependency_overrides.clear()
