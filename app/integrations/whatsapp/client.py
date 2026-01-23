# app/integrations/whatsapp/client.py
from __future__ import annotations

import json
import urllib.request
import urllib.error
from dataclasses import dataclass
from typing import Any, Optional

from app.core.config import settings


@dataclass
class WhatsAppSendResult:
    provider_message_id: Optional[str]
    raw: dict[str, Any]


class WhatsAppSendError(Exception):
    def __init__(self, *, status_code: int, error_code: str | None, error_message: str | None):
        self.status_code = status_code
        self.error_code = error_code
        self.error_message = error_message
        super().__init__(
            f"WhatsApp send failed: status={status_code} code={error_code} msg={error_message}")


def _build_messages_url() -> str:
    base = settings.whatsapp_base_url.rstrip("/")
    version = settings.whatsapp_api_version.strip("/")
    phone_number_id = settings.whatsapp_phone_number_id
    return f"{base}/{version}/{phone_number_id}/messages"


def send_text(*, to: str, body: str) -> WhatsAppSendResult:
    """
    Sends a simple WhatsApp text message via Cloud API.

    Uses standard library urllib to avoid adding new dependencies.
    Raises WhatsAppSendError on non-2xx.
    """
    if not settings.whatsapp_enabled:
        # Safety: caller should already check, but keep this as guardrail.
        return WhatsAppSendResult(provider_message_id=None, raw={"skipped": True})

    if not settings.whatsapp_access_token or not settings.whatsapp_phone_number_id:
        raise WhatsAppSendError(
            status_code=500,
            error_code="CONFIG_MISSING",
            error_message="WHATSAPP_ACCESS_TOKEN or WHATSAPP_PHONE_NUMBER_ID missing while WHATSAPP_ENABLED=true",
        )

    url = _build_messages_url()

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": body},
    }
    data = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(
        url=url,
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {settings.whatsapp_access_token}",
            "Content-Type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=settings.whatsapp_timeout_seconds) as resp:
            resp_body = resp.read().decode("utf-8") if resp else ""
            parsed = json.loads(resp_body) if resp_body else {}
            provider_message_id = None

            # WhatsApp Graph API typically returns {"messages":[{"id":"..."}]}
            msgs = parsed.get("messages") if isinstance(parsed, dict) else None
            if isinstance(msgs, list) and len(msgs) > 0 and isinstance(msgs[0], dict):
                provider_message_id = msgs[0].get("id")

            return WhatsAppSendResult(provider_message_id=provider_message_id, raw=parsed)

    except urllib.error.HTTPError as e:
        try:
            body_txt = e.read().decode("utf-8")
            parsed = json.loads(body_txt) if body_txt else {}
        except Exception:
            parsed = {}

        err = parsed.get("error") if isinstance(parsed, dict) else None
        error_code = str(err.get("code")) if isinstance(
            err, dict) and err.get("code") is not None else None
        error_message = err.get("message") if isinstance(err, dict) else None

        raise WhatsAppSendError(
            status_code=getattr(e, "code", 500) or 500,
            error_code=error_code,
            error_message=error_message,
        )

    except urllib.error.URLError as e:
        raise WhatsAppSendError(
            status_code=502,
            error_code="NETWORK_ERROR",
            error_message=str(e),
        )
