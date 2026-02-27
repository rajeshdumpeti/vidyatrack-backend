from app.core.phone import normalize_phone_for_otp, normalize_phone, whatsapp_destination


def test_normalize_phone_for_otp_preserves_e164_plus_1() -> None:
    assert normalize_phone_for_otp("+16198329657") == "+16198329657"


def test_normalize_phone_for_otp_preserves_e164_plus_91() -> None:
    assert normalize_phone_for_otp("+919876543210") == "+919876543210"


def test_normalize_phone_legacy_behavior_is_unchanged() -> None:
    assert normalize_phone("+16198329657") == "6198329657"


def test_whatsapp_destination_removes_plus_for_provider() -> None:
    assert whatsapp_destination("+16198329657") == "16198329657"
