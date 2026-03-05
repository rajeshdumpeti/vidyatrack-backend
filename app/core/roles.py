def normalize_role(role: str | None) -> str:
    return (role or "").strip().upper()
