import base64
import hmac
import json

from datetime import datetime, timezone
from typing import Generator
from app.db.session import SessionLocal
from datetime import datetime, timezone
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.core.config import settings

security = HTTPBearer(auto_error=False)


def get_db() -> Generator:
    """
    FastAPI dependency that provides a database session.

    Why this exists:
    - Ensures one DB session per request
    - Guarantees session is closed after request
    - Centralizes DB lifecycle management
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _jwt_decode_hs256(token: str) -> dict:
    try:
        header_b64, payload_b64, sig_b64 = token.split(".")
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_token")

    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    expected_sig = hmac.new(
        settings.jwt_secret.encode("utf-8"),
        signing_input,
        digestmod="sha256",
    ).digest()

    actual_sig = _b64url_decode(sig_b64)

    if not hmac.compare_digest(expected_sig, actual_sig):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_signature")

    payload = json.loads(_b64url_decode(payload_b64))

    now = int(datetime.now(timezone.utc).timestamp())
    if payload.get("exp") and payload["exp"] < now:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="token_expired")

    return payload


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="missing_token")

    token = credentials.credentials
    payload = _jwt_decode_hs256(token)

    return {
        "user_id": int(payload["sub"]),
        "school_id": payload["school_id"],
        "role": payload["role"],
    }


def require_management(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user.get("role") != "MANAGEMENT":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="insufficient_permissions",
        )
    return current_user


def require_teacher(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user.get("role") != "TEACHER":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="insufficient_permissions",
        )
    return current_user


def require_teacher_or_management_or_principal(
    current_user: dict = Depends(get_current_user),
) -> dict:
    if current_user["role"] not in ["TEACHER", "MANAGEMENT", "PRINCIPAL"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="insufficient_permissions",
        )
    return current_user


def require_principal(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user.get("role") != "PRINCIPAL":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="insufficient_permissions",
        )
    return current_user
