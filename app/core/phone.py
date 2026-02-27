import re


E164_RE = re.compile(r"^\+[1-9]\d{7,14}$")


def phone_candidates(phone: str) -> set[str]:
    trimmed = phone.strip()
    digits = "".join(ch for ch in trimmed if ch.isdigit())
    candidates: set[str] = set()
    if digits:
        candidates.add(digits)
        if len(digits) > 10:
            candidates.add(digits[-10:])
    candidates.add(trimmed)
    return candidates


def normalize_phone(phone: str) -> str:
    candidates = phone_candidates(phone)
    digits_only = next((c for c in candidates if c.isdigit()), "")
    if digits_only:
        return digits_only[-10:] if len(digits_only) > 10 else digits_only
    return phone.strip()


def normalize_phone_for_otp(phone: str) -> str:
    """Preserve E.164 format for OTP flows while allowing legacy numeric input."""
    trimmed = phone.strip()
    digits = "".join(ch for ch in trimmed if ch.isdigit())

    if trimmed.startswith("+") and digits:
        candidate = f"+{digits}"
        if E164_RE.match(candidate):
            return candidate

    if digits:
        return digits

    return trimmed


def whatsapp_destination(phone: str) -> str:
    """WhatsApp Cloud API expects international digits without a plus sign."""
    return "".join(ch for ch in phone if ch.isdigit())


def phone_country_code(phone: str) -> str:
    trimmed = phone.strip()
    if trimmed.startswith("+1"):
        return "1"
    if trimmed.startswith("+91"):
        return "91"
    if trimmed.startswith("+"):
        digits = whatsapp_destination(trimmed)
        if digits:
            return digits[:3]
    return "unknown"
