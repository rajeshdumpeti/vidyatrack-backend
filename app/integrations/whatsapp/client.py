from __future__ import annotations

import httpx
from typing import Optional

from app.core.config import settings


class WhatsAppSendError(Exception):
    def __init__(self, status_code: int, error_code: Optional[str], message: str):
        self.status_code = status_code
        self.error_code = error_code
        self.message = message
        super().__init__(f"WhatsApp send failed: {message}")


class WhatsAppClient:
    def __init__(self) -> None:
        if not settings.WHATSAPP_ACCESS_TOKEN:
            raise RuntimeError("WHATSAPP_ACCESS_TOKEN is not set")

        self.base_url = settings.WHATSAPP_BASE_URL.rstrip("/")
        self.api_version = settings.WHATSAPP_API_VERSION
        self.phone_number_id = settings.WHATSAPP_PHONE_NUMBER_ID
        self.timeout = settings.WHATSAPP_TIMEOUT_SECONDS

    def _messages_url(self) -> str:
        return (
            f"{self.base_url}/"
            f"{self.api_version}/"
            f"{self.phone_number_id}/messages"
        )

    def send_text(self, *, to: str, body: str) -> Optional[str]:
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {
                "body": body,
            },
        }

        headers = {
            "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
            "Content-Type": "application/json",
        }

        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(self._messages_url(),
                               json=payload, headers=headers)

        if resp.status_code // 100 != 2:
            data = {}
            try:
                data = resp.json()
            except Exception:
                pass

            error = data.get("error", {}) if isinstance(data, dict) else {}
            raise WhatsAppSendError(
                status_code=resp.status_code,
                error_code=str(error.get("code")) if error else None,
                message=error.get("message", resp.text),
            )

        data = resp.json()
        messages = data.get("messages") or []
        if messages and isinstance(messages, list):
            return messages[0].get("id")

        return None
