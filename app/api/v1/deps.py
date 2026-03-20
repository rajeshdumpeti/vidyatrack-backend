import base64
import hmac
import json
from datetime import datetime, timezone
from typing import Generator

from fastapi import Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.roles import normalize_role
from app.db.session import SessionLocal
from app.db.models.user import User
from app.db.models.user_school import UserSchool

security = HTTPBearer(auto_error=False)


def get_db() -> Generator:
    """Provides a database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _jwt_decode_hs256(token: str) -> dict:
    """Manual JWT decoding to verify signature and expiration."""
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
    db: Session = Depends(get_db)
) -> User:
    """Dependency to retrieve the authenticated user from the JWT."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="missing_token")

    token = credentials.credentials
    payload = _jwt_decode_hs256(token)

    user_id = int(payload["sub"])
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="user_not_found")

    return user

# --- ROLE-BASED ACCESS CONTROL ---


def require_management(current_user: User = Depends(get_current_user)) -> User:
    if normalize_role(current_user.role) != "MANAGEMENT":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="insufficient_permissions",
        )
    return current_user


def require_teacher(current_user: User = Depends(get_current_user)) -> User:
    if normalize_role(current_user.role) != "TEACHER":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="insufficient_permissions",
        )
    return current_user


def require_principal(current_user: User = Depends(get_current_user)) -> User:
    if normalize_role(current_user.role) != "PRINCIPAL":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="insufficient_permissions",
        )
    return current_user


def require_super_admin(current_user: User = Depends(get_current_user)) -> User:
    if normalize_role(current_user.role) != "SUPER_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="insufficient_permissions",
        )
    return current_user


def require_teacher_or_management_or_principal(
    current_user: User = Depends(get_current_user),
) -> User:
    if normalize_role(current_user.role) not in ["TEACHER", "MANAGEMENT", "PRINCIPAL"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="insufficient_permissions",
        )
    return current_user


def require_teacher_or_principal(
    current_user: User = Depends(get_current_user),
) -> User:
    if normalize_role(current_user.role) not in ["TEACHER", "PRINCIPAL"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="insufficient_permissions",
        )
    return current_user

# --- SCHOOL CONTEXT VALIDATION ---


def get_valid_school_id(
    school_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> int:
    """
    Verifies the user has an explicit mapping to the school_id provided.
    This prevents users from 'guessing' other school IDs in the query string.
    """
    access = db.query(UserSchool).filter(
        UserSchool.user_id == current_user.id,
        UserSchool.school_id == school_id
    ).first()

    if not access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User {current_user.id} does not have access to school {school_id}."
        )

    return school_id
