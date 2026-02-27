import json
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.core.config import settings


@dataclass
class EmailSendResult:
    success: bool
    provider_message_id: str | None
    status_code: int
    provider_error_code: str | None = None
    provider_error_message: str | None = None


def _parse_error_response(raw_body: str) -> tuple[str | None, str | None]:
    if not raw_body:
        return None, None

    try:
        parsed = json.loads(raw_body)
    except json.JSONDecodeError:
        return None, raw_body[:300]

    if not isinstance(parsed, dict):
        return None, raw_body[:300]

    # Brevo often returns {"code":"xxx","message":"..."}.
    code = parsed.get("code")
    message = parsed.get("message")
    return (str(code) if code is not None else None), (
        str(message) if message is not None else raw_body[:300]
    )


def send_otp_email(to_email: str, otp: str) -> EmailSendResult:
    if not settings.brevo_api_key:
        raise ValueError("BREVO_API_KEY is not configured")
    if not settings.brevo_sender_email:
        raise ValueError("BREVO_SENDER_EMAIL is not configured")

    base_url = settings.brevo_api_base_url.rstrip("/")
    url = f"{base_url}/smtp/email"

    payload = {
        "sender": {
            "name": settings.brevo_sender_name,
            "email": settings.brevo_sender_email,
        },
        "to": [{"email": to_email}],
        "subject": settings.brevo_otp_subject,
        "textContent": (
            f"Your VidyaTrack OTP is {otp}. "
            "It expires in 5 minutes. Do not share this code."
        ),
    }

    request = Request(
        url=url,
        headers={
            "accept": "application/json",
            "api-key": settings.brevo_api_key,
            "content-type": "application/json",
        },
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
    )

    try:
        with urlopen(request, timeout=10) as response:
            status_code = response.getcode()
            body = response.read().decode("utf-8")
            parsed = json.loads(body) if body else {}
            provider_message_id = None
            if isinstance(parsed, dict):
                # Brevo returns "messageId" on accepted send.
                maybe_id = parsed.get("messageId")
                if maybe_id is not None:
                    provider_message_id = str(maybe_id)
            return EmailSendResult(
                success=200 <= status_code < 300,
                provider_message_id=provider_message_id,
                status_code=status_code,
            )
    except HTTPError as exc:
        raw_error = exc.read().decode("utf-8", errors="ignore")
        provider_error_code, provider_error_message = _parse_error_response(raw_error)
        return EmailSendResult(
            success=False,
            provider_message_id=None,
            status_code=exc.code,
            provider_error_code=provider_error_code,
            provider_error_message=provider_error_message,
        )
    except URLError:
        return EmailSendResult(
            success=False,
            provider_message_id=None,
            status_code=0,
            provider_error_message="network_error",
        )

