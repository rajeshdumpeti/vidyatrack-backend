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
