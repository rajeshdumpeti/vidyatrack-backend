import hashlib
import secrets
import base64
import hmac
import json
import logging

from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException, status, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user, get_db
from app.core.phone import normalize_phone_for_otp, phone_candidates, phone_country_code
from app.db.models.otp_request import OtpRequest
from app.db.models.user import User
from app.core.config import settings
from app.db.models.user_school import UserSchool
from app.integrations.email.brevo import send_otp_email
from app.integrations.whatsapp.client import send_otp_template

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)

# Pilot-safe "pepper" for hashing. Later we should replace this with Settings.SECRET_KEY.
OTP_TTL_MINUTES = settings.otp_ttl_minutes
OTP_PEPPER = settings.otp_pepper
JWT_SECRET = settings.jwt_secret
JWT_TTL_MINUTES = settings.jwt_ttl_minutes
OTP_RATE_LIMIT_SECONDS = 30
OTP_MAX_PER_HOUR = 5


class OtpRequestIn(BaseModel):
    phone: str


class OtpRequestOut(BaseModel):
    status: str
    delivery_channel: str


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

    header_b64 = _b64url_encode(json.dumps(
        header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64url_encode(json.dumps(
        payload, separators=(",", ":")).encode("utf-8"))

    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    sig = hmac.new(JWT_SECRET.encode("utf-8"),
                   signing_input, hashlib.sha256).digest()
    sig_b64 = _b64url_encode(sig)

    return f"{header_b64}.{payload_b64}.{sig_b64}"


def _phone_last4(phone: str) -> str:
    return phone[-4:] if len(phone) >= 4 else phone


def _is_local_request(request: Request) -> bool:
    local_hosts = {"localhost", "127.0.0.1", "::1"}
    request_host = (request.url.hostname or "").lower()
    client_host = (request.client.host if request.client else "").lower()
    return request_host in local_hosts or client_host in local_hosts


@router.post("/otp/request", response_model=OtpRequestOut, status_code=200)
def request_otp(
    payload: OtpRequestIn,
    request: Request,
    db: Session = Depends(get_db),
):
    trace_id = request.headers.get("x-request-id", "n/a")
    normalized_phone = normalize_phone_for_otp(payload.phone)
    country_code = phone_country_code(normalized_phone)
    now = datetime.now(timezone.utc)

    recent_cutoff = now - timedelta(seconds=OTP_RATE_LIMIT_SECONDS)
    recent_request = (
        db.query(OtpRequest)
        .filter(
            OtpRequest.phone == normalized_phone,
            OtpRequest.created_at >= recent_cutoff,
        )
        .first()
    )
    if recent_request:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="otp_rate_limited",
        )

    hourly_cutoff = now - timedelta(hours=1)
    hourly_count = (
        db.query(OtpRequest)
        .filter(
            OtpRequest.phone == normalized_phone,
            OtpRequest.created_at >= hourly_cutoff,
        )
        .count()
    )
    if hourly_count >= OTP_MAX_PER_HOUR:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="otp_too_many_requests",
        )

    otp = f"{secrets.randbelow(10_000):04d}"
    otp_hash = _hash_otp(normalized_phone, otp)

    if (settings.debug and settings.otp_debug_log_plaintext) or _is_local_request(request):
        logger.info(
            (
                "otp debug plaintext trace_id=%s phone_country_code=%s "
                "phone_last4=%s otp=%s"
            ),
            trace_id,
            country_code,
            _phone_last4(normalized_phone),
            otp,
        )

    expires_at = now + timedelta(minutes=OTP_TTL_MINUTES)

    row = OtpRequest(
        phone=normalized_phone,
        otp_hash=otp_hash,
        expires_at=expires_at,
        attempt_count=0,
        channel="WHATSAPP",
        status="PENDING",
        attempts=1,
        provider_message_id=None,
        sent_at=None,
        consumed_at=None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    logger.info(
        (
            "otp request persisted trace_id=%s phone_country_code=%s "
            "phone_last4=%s otp_request_id=%s"
        ),
        trace_id,
        country_code,
        _phone_last4(normalized_phone),
        row.id,
    )

    if settings.otp_delivery_mode.strip().lower() == "local_log_only":
        row.status = "SENT"
        row.channel = "LOCAL"
        row.provider_message_id = "local_log_only"
        row.sent_at = datetime.now(timezone.utc)
        db.add(row)
        db.commit()
        logger.info(
            (
                "otp local delivery trace_id=%s phone_country_code=%s "
                "phone_last4=%s otp_request_id=%s mode=%s otp========================================%s"
            ),
            trace_id,
            country_code,
            _phone_last4(normalized_phone),
            row.id,
            "local_log_only",
            otp,
        )
        # Keep response shape stable for frontend.
        return {"status": "otp_sent", "delivery_channel": "whatsapp"}

    wa_result = None
    try:
        wa_result = send_otp_template(phone=normalized_phone, otp=otp)
    except Exception:
        row.status = "FAILED"
        db.add(row)
        db.commit()
        logger.exception(
            (
                "whatsapp otp send failed trace_id=%s phone_country_code=%s "
                "phone_last4=%s otp_request_id=%s mapped_backend_error_code=%s"
            ),
            trace_id,
            country_code,
            _phone_last4(normalized_phone),
            row.id,
            "whatsapp_delivery_failed",
        )

    if wa_result is not None:
        row.provider_message_id = wa_result.provider_message_id

        logger.info(
            (
                "whatsapp otp send attempted trace_id=%s phone_country_code=%s phone_last4=%s "
                "otp_request_id=%s whatsapp_status_code=%s provider_message_id=%s "
                "provider_error_code=%s provider_error_message=%s"
            ),
            trace_id,
            country_code,
            _phone_last4(normalized_phone),
            row.id,
            wa_result.status_code,
            wa_result.provider_message_id,
            wa_result.provider_error_code,
            wa_result.provider_error_message,
        )

        if wa_result.success:
            row.status = "SENT"
            row.channel = "WHATSAPP"
            row.sent_at = datetime.now(timezone.utc)
            db.add(row)
            db.commit()
            return {"status": "otp_sent", "delivery_channel": "whatsapp"}

        row.status = "FAILED"
        db.add(row)
        db.commit()

    # WhatsApp failed; fallback to email using user's registered email, if available.
    user = (
        db.query(User)
        .filter(User.is_active.is_(True))
        .filter(User.phone.in_(phone_candidates(normalized_phone)))
        .first()
    )
    email = getattr(user, "email", None) if user else None

    if email:
        try:
            email_result = send_otp_email(to_email=email, otp=otp)
        except Exception:
            logger.exception(
                (
                    "email otp fallback failed trace_id=%s phone_country_code=%s "
                    "phone_last4=%s otp_request_id=%s mapped_backend_error_code=%s"
                ),
                trace_id,
                country_code,
                _phone_last4(normalized_phone),
                row.id,
                "whatsapp_delivery_failed",
            )
        else:
            logger.info(
                (
                    "email otp send attempted trace_id=%s phone_country_code=%s phone_last4=%s "
                    "otp_request_id=%s email_status_code=%s provider_message_id=%s "
                    "provider_error_code=%s provider_error_message=%s"
                ),
                trace_id,
                country_code,
                _phone_last4(normalized_phone),
                row.id,
                email_result.status_code,
                email_result.provider_message_id,
                email_result.provider_error_code,
                email_result.provider_error_message,
            )
            if email_result.success:
                row.status = "SENT"
                row.channel = "EMAIL"
                row.provider_message_id = email_result.provider_message_id
                row.sent_at = datetime.now(timezone.utc)
                db.add(row)
                db.commit()
                return {"status": "otp_sent", "delivery_channel": "email"}

    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="whatsapp_delivery_failed",
    )


@router.post("/otp/verify", response_model=TokenOut, status_code=200)
def verify_otp(payload: OtpVerifyIn, db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    normalized_phone = normalize_phone_for_otp(payload.phone)

    otp_row = (
        db.query(OtpRequest)
        .filter(
            OtpRequest.phone == normalized_phone,
            OtpRequest.consumed_at.is_(None),
            OtpRequest.expires_at > now,
        )
        .order_by(OtpRequest.id.desc())
        .first()
    )

    if not otp_row:
        latest_any = (
            db.query(OtpRequest)
            .filter(
                OtpRequest.phone == normalized_phone,
                OtpRequest.consumed_at.is_(None),
            )
            .order_by(OtpRequest.id.desc())
            .first()
        )
        if latest_any and latest_any.expires_at <= now:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="otp_expired",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="otp_not_found",
        )

    expected_hash = otp_row.otp_hash
    provided_hash = _hash_otp(normalized_phone, payload.otp)

    if not hmac.compare_digest(expected_hash, provided_hash):
        otp_row.attempt_count = (otp_row.attempt_count or 0) + 1
        db.add(otp_row)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="otp_invalid")

    otp_row.consumed_at = now
    db.add(otp_row)
    db.commit()

    user = (
        db.query(User)
        .filter(User.is_active.is_(True))
        .filter(User.phone.in_(phone_candidates(payload.phone)))
        .first()
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="user_not_found")

    exp = now + timedelta(minutes=JWT_TTL_MINUTES)

    token_payload = {
        "sub": str(user.id),
        # We remove the single school_id here.
        # The frontend will now call a separate /me or /user/schools
        # endpoint to see which schools this user can access.
        "role": user.role,
        "is_super_admin": user.role == "super_admin",
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }

    token = _jwt_encode_hs256(token_payload)
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me")
def get_me(
    db: Session = Depends(get_db),
    # This helper must return the User object
    current_user: User = Depends(get_current_user),
):
    # Fetch all schools linked to this user
    user_schools = db.query(UserSchool).filter(
        UserSchool.user_id == current_user.id).all()

    return {
        "id": current_user.id,
        "phone": current_user.phone,
        "role": current_user.role,
        "schools": [
            {
                "id": us.school_id,
                "name": us.school.name,
                "role": us.role
            } for us in user_schools
        ]
    }
