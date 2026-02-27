import io
import json
from urllib.error import HTTPError

import pytest

from app.core.config import settings
from app.integrations.whatsapp.client import send_otp_template


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
def _wa_settings(monkeypatch):
    monkeypatch.setattr(settings, "whatsapp_access_token", "token")
    monkeypatch.setattr(settings, "whatsapp_phone_number_id", "123456")
    monkeypatch.setattr(settings, "whatsapp_waba_id", "123456")
    monkeypatch.setattr(settings, "whatsapp_api_version", "v22.0")
    monkeypatch.setattr(settings, "whatsapp_otp_template_name", "VidyaTrack")
    monkeypatch.setattr(settings, "whatsapp_otp_template_lang", "en_US")


@pytest.mark.parametrize(
    "phone,expected_to",
    [
        ("+16198329657", "16198329657"),
        ("+919876543210", "919876543210"),
    ],
)
def test_send_otp_template_builds_whatsapp_destination(_wa_settings, monkeypatch, phone: str, expected_to: str):
    captured = {}

    def _fake_urlopen(request, timeout=10):
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        return _FakeResponse(200, {"messages": [{"id": "wamid.test"}]})

    monkeypatch.setattr(
        "app.integrations.whatsapp.client.urlopen", _fake_urlopen)

    result = send_otp_template(phone=phone, otp="1234")

    assert result.success is True
    assert result.status_code == 200
    assert result.provider_message_id == "wamid.test"
    assert captured["payload"]["to"] == expected_to


def test_send_otp_template_parses_provider_error(_wa_settings, monkeypatch):
    body = {
        "error": {
            "message": "Recipient phone number not in allowed list",
            "code": 131030,
        }
    }

    def _fake_urlopen(request, timeout=10):
        raise HTTPError(
            request.full_url,
            400,
            "Bad Request",
            hdrs=None,
            fp=io.BytesIO(json.dumps(body).encode("utf-8")),
        )

    monkeypatch.setattr(
        "app.integrations.whatsapp.client.urlopen", _fake_urlopen)

    result = send_otp_template(phone="+16198329657", otp="1234")

    assert result.success is False
    assert result.status_code == 400
    assert result.provider_error_code == 131030
    assert result.provider_error_message == "Recipient phone number not in allowed list"


def test_send_otp_template_hello_world_sends_no_components(_wa_settings, monkeypatch):
    captured = {}
    monkeypatch.setattr(settings, "whatsapp_otp_template_name", "hello_world")

    def _fake_urlopen(request, timeout=10):
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        return _FakeResponse(200, {"messages": [{"id": "wamid.hello"}]})

    monkeypatch.setattr(
        "app.integrations.whatsapp.client.urlopen", _fake_urlopen)

    result = send_otp_template(phone="+16198329657", otp="1234")

    assert result.success is True
    assert captured["payload"]["template"]["name"] == "hello_world"
    assert "components" not in captured["payload"]["template"]
