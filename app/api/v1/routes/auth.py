import hashlib
import secrets
import base64
import hmac
import json
import os

from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.v1.deps import get_db
from app.db.models.otp_request import OtpRequest
from app.db.models.user import User
from app.core.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])

# Pilot-safe "pepper" for hashing. Later we should replace this with Settings.SECRET_KEY.
OTP_TTL_MINUTES = settings.otp_ttl_minutes
OTP_PEPPER = settings.otp_pepper
JWT_SECRET = settings.jwt_secret
JWT_TTL_MINUTES = settings.jwt_ttl_minutes


class OtpRequestIn(BaseModel):
    phone: str


class OtpRequestOut(BaseModel):
    status: str

class OtpVerifyIn(BaseModel):
    phone: str
    otp: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


def _hash_otp(phone: str, otp: str) -> str:
    payload = f"{phone}:{otp}:{OTP_PEPPER}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()

def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def _jwt_encode_hs256(payload: dict) -> str:
    header = {"alg": "HS256", "typ": "JWT"}

    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))

    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    sig = hmac.new(JWT_SECRET.encode("utf-8"), signing_input, hashlib.sha256).digest()
    sig_b64 = _b64url_encode(sig)

    return f"{header_b64}.{payload_b64}.{sig_b64}"



@router.post("/otp/request", response_model=OtpRequestOut, status_code=200)
def request_otp(payload: OtpRequestIn, db: Session = Depends(get_db)):
    otp = f"{secrets.randbelow(1_000_000):06d}"
    otp_hash = _hash_otp(payload.phone, otp)

    expires_at = datetime.now(timezone.utc) + timedelta(minutes=OTP_TTL_MINUTES)

    row = OtpRequest(
        phone=payload.phone,
        otp_hash=otp_hash,
        expires_at=expires_at,
        attempt_count=0,
        consumed_at=None,
    )
    db.add(row)
    db.commit()

    # Pilot mode: OTP "send" is console/log only
    print(f"[OTP] phone={payload.phone} otp={otp} expires_in_min={OTP_TTL_MINUTES}")

    return {"status": "otp_sent"}



@router.post("/otp/verify", response_model=TokenOut, status_code=200)
def verify_otp(payload: OtpVerifyIn, db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)

    otp_row = (
        db.query(OtpRequest)
        .filter(
            OtpRequest.phone == payload.phone,
            OtpRequest.consumed_at.is_(None),
        )
        .order_by(OtpRequest.id.desc())
        .first()
    )

    if not otp_row:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="otp_not_found")

    if otp_row.expires_at <= now:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="otp_expired")

    expected_hash = otp_row.otp_hash
    provided_hash = _hash_otp(payload.phone, payload.otp)

    if not hmac.compare_digest(expected_hash, provided_hash):
        otp_row.attempt_count = (otp_row.attempt_count or 0) + 1
        db.add(otp_row)
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="otp_invalid")

    otp_row.consumed_at = now
    db.add(otp_row)
    db.commit()

    user = (
        db.query(User)
        .filter(User.phone == payload.phone, User.is_active.is_(True))
        .first()
    )
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user_not_found")

    exp = now + timedelta(minutes=JWT_TTL_MINUTES)

    token_payload = {
        "sub": str(user.id),
        "school_id": user.school_id,
        "role": user.role,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }

    token = _jwt_encode_hs256(token_payload)
    return {"access_token": token, "token_type": "bearer"}

