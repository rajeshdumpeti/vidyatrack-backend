from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1.deps import get_db
from app.db.models.otp_request import OtpRequest
from app.db.models.user import User
from app.integrations.whatsapp.client import WhatsAppSendResult
from app.main import app


@pytest.fixture()
def otp_client(monkeypatch):
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    OtpRequest.__table__.create(bind=engine)
    User.__table__.create(bind=engine)

    def _override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db

    with TestClient(app) as test_client:
        yield test_client, TestingSessionLocal

    app.dependency_overrides.clear()


@pytest.mark.parametrize("phone", ["+16198329657", "+919876543210"])
def test_otp_request_success_for_plus_1_and_plus_91(otp_client, monkeypatch, phone: str):
    client, session_factory = otp_client

    def _mock_send(phone: str, otp: str):
        return WhatsAppSendResult(success=True, provider_message_id="wamid.ok", status_code=200)

    monkeypatch.setattr("app.api.v1.routes.auth.send_otp_template", _mock_send)

    response = client.post(
        "/api/v1/auth/otp/request",
        json={"phone": phone},
        headers={"x-request-id": f"test-{phone}"},
    )

    assert response.status_code == 200
    assert response.json() == {"status": "otp_sent", "delivery_channel": "whatsapp"}

    db = session_factory()
    try:
        row = db.query(OtpRequest).filter(OtpRequest.phone == phone).order_by(OtpRequest.id.desc()).first()
        assert row is not None
        assert row.status == "SENT"
        assert row.provider_message_id == "wamid.ok"
        assert isinstance(row.sent_at, datetime)
        assert row.sent_at is not None
    finally:
        db.close()


def test_otp_request_failure_payload_shape(otp_client, monkeypatch):
    client, session_factory = otp_client

    def _mock_send(phone: str, otp: str):
        return WhatsAppSendResult(
            success=False,
            provider_message_id=None,
            status_code=400,
            provider_error_code=131030,
            provider_error_message="Recipient phone number not in allowed list",
        )

    monkeypatch.setattr("app.api.v1.routes.auth.send_otp_template", _mock_send)

    response = client.post(
        "/api/v1/auth/otp/request",
        json={"phone": "+16198329657"},
        headers={"x-request-id": "test-failure"},
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "whatsapp_delivery_failed"}

    db = session_factory()
    try:
        row = db.query(OtpRequest).filter(OtpRequest.phone == "+16198329657").order_by(OtpRequest.id.desc()).first()
        assert row is not None
        assert row.status == "FAILED"
    finally:
        db.close()


def test_otp_request_falls_back_to_email_when_whatsapp_fails(otp_client, monkeypatch):
    client, session_factory = otp_client
    db = session_factory()
    try:
        db.add(
            User(
                phone="+16198329657",
                email="teacher@example.com",
                role="teacher",
                is_active=True,
                can_create_school=False,
                max_schools=None,
            )
        )
        db.commit()
    finally:
        db.close()

    def _mock_wa_send(phone: str, otp: str):
        return WhatsAppSendResult(
            success=False,
            provider_message_id=None,
            status_code=400,
            provider_error_code=131030,
            provider_error_message="not allowed",
        )

    class _EmailResult:
        success = True
        provider_message_id = "email-123"
        status_code = 201
        provider_error_code = None
        provider_error_message = None

    def _mock_email_send(to_email: str, otp: str):
        assert to_email == "teacher@example.com"
        assert len(otp) == 4
        return _EmailResult()

    monkeypatch.setattr("app.api.v1.routes.auth.send_otp_template", _mock_wa_send)
    monkeypatch.setattr("app.api.v1.routes.auth.send_otp_email", _mock_email_send)

    response = client.post(
        "/api/v1/auth/otp/request",
        json={"phone": "+16198329657"},
        headers={"x-request-id": "test-fallback-email"},
    )

    assert response.status_code == 200
    assert response.json() == {"status": "otp_sent", "delivery_channel": "email"}

    db = session_factory()
    try:
        row = db.query(OtpRequest).filter(OtpRequest.phone == "+16198329657").order_by(OtpRequest.id.desc()).first()
        assert row is not None
        assert row.status == "SENT"
        assert row.channel == "EMAIL"
        assert row.provider_message_id == "email-123"
    finally:
        db.close()


def test_otp_request_falls_back_to_email_when_whatsapp_raises(otp_client, monkeypatch):
    client, session_factory = otp_client
    db = session_factory()
    try:
        db.add(
            User(
                phone="+919876543210",
                email="principal@example.com",
                role="principal",
                is_active=True,
                can_create_school=False,
                max_schools=None,
            )
        )
        db.commit()
    finally:
        db.close()

    def _mock_wa_send(phone: str, otp: str):
        raise RuntimeError("provider timeout")

    class _EmailResult:
        success = True
        provider_message_id = "email-456"
        status_code = 201
        provider_error_code = None
        provider_error_message = None

    def _mock_email_send(to_email: str, otp: str):
        assert to_email == "principal@example.com"
        return _EmailResult()

    monkeypatch.setattr("app.api.v1.routes.auth.send_otp_template", _mock_wa_send)
    monkeypatch.setattr("app.api.v1.routes.auth.send_otp_email", _mock_email_send)

    response = client.post(
        "/api/v1/auth/otp/request",
        json={"phone": "+919876543210"},
        headers={"x-request-id": "test-fallback-on-exception"},
    )

    assert response.status_code == 200
    assert response.json() == {"status": "otp_sent", "delivery_channel": "email"}
