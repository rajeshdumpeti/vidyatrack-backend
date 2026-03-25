import json
import ssl
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.core.config import settings
from app.core.phone import whatsapp_destination
ssl._create_default_https_context = ssl._create_unverified_context


@dataclass
class WhatsAppSendResult:
    success: bool
    provider_message_id: str | None
    status_code: int
    provider_error_code: int | None = None
    provider_error_message: str | None = None


def _parse_error_response(raw_body: str) -> tuple[int | None, str | None]:
    if not raw_body:
        return None, None

    try:
        parsed = json.loads(raw_body)
    except json.JSONDecodeError:
        return None, raw_body[:300]

    if not isinstance(parsed, dict):
        return None, raw_body[:300]

    error_payload = parsed.get("error")
    if not isinstance(error_payload, dict):
        return None, raw_body[:300]

    code = error_payload.get("code")
    message = error_payload.get("message")

    try:
        parsed_code = int(code) if code is not None else None
    except (TypeError, ValueError):
        parsed_code = None

    return parsed_code, message


def send_otp_template(phone: str, otp: str) -> WhatsAppSendResult:
    missing = next(
        (name for name, val in [
            ("WHATSAPP_ACCESS_TOKEN", settings.whatsapp_access_token),
            ("WHATSAPP_PHONE_NUMBER_ID", settings.whatsapp_phone_number_id),
            ("WHATSAPP_OTP_TEMPLATE_NAME", settings.whatsapp_otp_template_name),
            ("WHATSAPP_WABA_ID", settings.whatsapp_waba_id),
        ] if not val),
        None,
    )
    if missing:
        return WhatsAppSendResult(
            success=False,
            provider_message_id=None,
            status_code=0,
            provider_error_message=f"{missing} is not configured",
        )

    version = settings.whatsapp_api_version.strip("/")
    phone_id = settings.whatsapp_phone_number_id.strip("/")

    url = f"https://graph.facebook.com/{version}/{phone_id}/messages"

    payload = {
        "messaging_product": "whatsapp",
        "to": whatsapp_destination(phone),
        "type": "template",
        "template": {
            "name": settings.whatsapp_otp_template_name,
            "language": {"code": settings.whatsapp_otp_template_lang},
        },
    }

    # Meta's built-in hello_world template expects zero parameters.
    if settings.whatsapp_otp_template_name != "hello_world":
        payload["template"]["components"] = [
            {
                "type": "body",
                "parameters": [
                    {
                        "type": "text",
                        "text": otp,
                    }
                ],
            }
        ]

    request = Request(
        url=url,
        headers={
            "Authorization": f"Bearer {settings.whatsapp_access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
    )

    try:
        with urlopen(request, timeout=10) as response:
            status_code = response.getcode()
            body = response.read().decode("utf-8")
            parsed = json.loads(body) if body else {}
            messages = parsed.get("messages") if isinstance(
                parsed, dict) else None
            provider_message_id = None
            if isinstance(messages, list) and messages:
                first = messages[0]
                if isinstance(first, dict):
                    provider_message_id = first.get("id")
            return WhatsAppSendResult(
                success=200 <= status_code < 300,
                provider_message_id=provider_message_id,
                status_code=status_code,
            )
    except HTTPError as exc:
        raw_error = exc.read().decode("utf-8", errors="ignore")
        provider_error_code, provider_error_message = _parse_error_response(
            raw_error)
        return WhatsAppSendResult(
            success=False,
            provider_message_id=None,
            status_code=exc.code,
            provider_error_code=provider_error_code,
            provider_error_message=provider_error_message,
        )
    except URLError:
        return WhatsAppSendResult(
            success=False,
            provider_message_id=None,
            status_code=0,
            provider_error_message="network_error",
        )
