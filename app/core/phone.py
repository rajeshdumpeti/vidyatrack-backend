"""
Phone normalisation — single source of truth.

All phone numbers are stored and compared in E.164 format:
    +<country_code><subscriber_number>
    e.g. +919876543210  +16198329657

Rules applied to raw user input (digits-only, partial E.164, full E.164):
  * Already E.164  (+<digits>, 8-15 total digits)  → returned as-is
  * 10 digits starting with 6-9                     → +91 prefix (Indian mobile)
  * 11 digits starting with 91                      → +91 prefix
  * 11 digits starting with 1                       → +1  prefix (NANP)
  * 12 digits starting with 91                      → +91 prefix
  * Anything else                                   → ValueError (rejected at API layer)

Never call this after the value is stored; stored values are already canonical.
"""
from __future__ import annotations

import re

_E164_RE = re.compile(r"^\+[1-9]\d{7,14}$")


def to_e164(raw: str) -> str:
    """
    Normalise *raw* to E.164.  Raises ValueError for unrecognisable input.
    This is the only normalisation function that should be called.
    """
    if not raw:
        raise ValueError("Phone number must not be empty.")

    trimmed = raw.strip()
    digits = re.sub(r"\D", "", trimmed)

    # Already well-formed E.164
    if trimmed.startswith("+") and _E164_RE.match(trimmed):
        return trimmed

    # Bare E.164 digits with implicit +
    if trimmed.startswith("+"):
        candidate = f"+{digits}"
        if _E164_RE.match(candidate):
            return candidate

    n = len(digits)

    # Indian 10-digit mobile (starts 6-9)
    if n == 10 and digits[0] in "6789":
        return f"+91{digits}"

    # Indian with country code but no +: 91XXXXXXXXXX
    if n == 12 and digits.startswith("91"):
        return f"+{digits}"

    # Indian 10-digit with leading 0 (landline style) — strip 0
    if n == 11 and digits.startswith("0") and digits[1] in "6789":
        return f"+91{digits[1:]}"

    # NANP: 1XXXXXXXXXX (US/Canada)
    if n == 11 and digits.startswith("1"):
        return f"+{digits}"

    # 10-digit NANP without country code
    if n == 10 and digits[0] in "23456789":
        return f"+1{digits}"

    raise ValueError(
        f"Cannot normalise '{raw}' to E.164. "
        "Please provide the number with country code, e.g. +919876543210."
    )


def whatsapp_destination(phone: str) -> str:
    """WhatsApp Cloud API expects international digits without a plus sign."""
    return re.sub(r"\D", "", phone)


def phone_country_code(phone: str) -> str:
    if phone.startswith("+1"):
        return "1"
    if phone.startswith("+91"):
        return "91"
    if phone.startswith("+"):
        digits = whatsapp_destination(phone)
        return digits[:3] if digits else "unknown"
    return "unknown"


# ---------------------------------------------------------------------------
# Legacy shims — kept so nothing breaks while callers are migrated.
# New code must call to_e164() directly.
# ---------------------------------------------------------------------------

def normalize_phone_for_otp(phone: str) -> str:
    """Deprecated shim — use to_e164()."""
    return to_e164(phone)


def normalize_phone(phone: str) -> str:
    """Deprecated shim — use to_e164()."""
    return to_e164(phone)


def phone_candidates(phone: str) -> set[str]:
    """
    Deprecated — existed to work around inconsistent storage formats.
    Now that all phones are stored as E.164, a single exact lookup suffices.
    Kept only so old call-sites don't crash until they are cleaned up.
    """
    try:
        canonical = to_e164(phone)
        return {canonical}
    except ValueError:
        return {phone.strip()}
