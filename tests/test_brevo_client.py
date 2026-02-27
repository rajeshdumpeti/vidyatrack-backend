import io
import json
from urllib.error import HTTPError

import pytest

from app.core.config import settings
from app.integrations.email.brevo import send_otp_email


class _FakeResponse:
    def __init__(self, status_code: int, body: dict):
        self._status_code = status_code
        self._body = json.dumps(body).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def getcode(self) -> int:
        return self._status_code

    def read(self) -> bytes:
        return self._body


@pytest.fixture()
def _brevo_settings(monkeypatch):
    monkeypatch.setattr(settings, "brevo_api_key", "key")
    monkeypatch.setattr(settings, "brevo_api_base_url", "https://api.brevo.com/v3")
    monkeypatch.setattr(settings, "brevo_sender_email", "no-reply@example.com")
    monkeypatch.setattr(settings, "brevo_sender_name", "VidyaTrack")
    monkeypatch.setattr(settings, "brevo_otp_subject", "Your VidyaTrack OTP")


def test_send_otp_email_success(_brevo_settings, monkeypatch):
    captured = {}

    def _fake_urlopen(request, timeout=10):
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        return _FakeResponse(201, {"messageId": "<abc@brevo>"})

    monkeypatch.setattr("app.integrations.email.brevo.urlopen", _fake_urlopen)

    result = send_otp_email("teacher@example.com", "1234")

    assert result.success is True
    assert result.status_code == 201
    assert result.provider_message_id == "<abc@brevo>"
    assert captured["payload"]["to"] == [{"email": "teacher@example.com"}]


def test_send_otp_email_parses_provider_error(_brevo_settings, monkeypatch):
    body = {"code": "invalid_parameter", "message": "Invalid email"}

    def _fake_urlopen(request, timeout=10):
        raise HTTPError(
            request.full_url,
            400,
            "Bad Request",
            hdrs=None,
            fp=io.BytesIO(json.dumps(body).encode("utf-8")),
        )

    monkeypatch.setattr("app.integrations.email.brevo.urlopen", _fake_urlopen)

    result = send_otp_email("bad", "1234")

    assert result.success is False
    assert result.status_code == 400
    assert result.provider_error_code == "invalid_parameter"
    assert result.provider_error_message == "Invalid email"

