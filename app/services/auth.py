from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from fastapi import HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.phone import normalize_phone_for_otp, phone_candidates, phone_country_code
from app.core.roles import normalize_role
from app.db.models.otp_request import OtpRequest
from app.db.models.user import User
from app.db.repositories import auth as auth_repository

logger = logging.getLogger(__name__)

OTP_RATE_LIMIT_SECONDS = 30
OTP_MAX_PER_HOUR = 5
OTP_MAX_VERIFY_ATTEMPTS = 5


def _hash_otp(phone: str, otp: str, *, otp_pepper: str) -> str:
    payload = f"{phone}:{otp}:{otp_pepper}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def _jwt_encode_hs256(payload: dict[str, Any], *, jwt_secret: str) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    sig = hmac.new(jwt_secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    sig_b64 = _b64url_encode(sig)
    return f"{header_b64}.{payload_b64}.{sig_b64}"


def _phone_last4(phone: str) -> str:
    return phone[-4:] if len(phone) >= 4 else phone


def _is_local_request(request: Request) -> bool:
    local_hosts = {"localhost", "127.0.0.1", "::1"}
    request_host = (request.url.hostname or "").lower()
    client_host = (request.client.host if request.client else "").lower()
    return request_host in local_hosts or client_host in local_hosts


def request_otp(
    *,
    payload_phone: str,
    request: Request,
    db: Session,
    otp_ttl_minutes: int,
    otp_pepper: str,
    debug: bool,
    otp_debug_log_plaintext: bool,
    otp_delivery_mode: str,
    send_otp_template: Callable[..., Any],
    send_otp_email: Callable[..., Any],
) -> dict[str, str]:
    trace_id = request.headers.get("x-request-id", "n/a")
    normalized_phone = normalize_phone_for_otp(payload_phone)
    country_code = phone_country_code(normalized_phone)
    delivery_mode = otp_delivery_mode.strip().lower()
    now = datetime.now(timezone.utc)

    recent_cutoff = now - timedelta(seconds=OTP_RATE_LIMIT_SECONDS)
    recent_request = auth_repository.get_recent_otp_request(
        db,
        phone=normalized_phone,
        recent_cutoff=recent_cutoff,
    )
    if recent_request:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="otp_rate_limited",
        )

    hourly_cutoff = now - timedelta(hours=1)
    hourly_count = auth_repository.count_hourly_otp_requests(
        db,
        phone=normalized_phone,
        hourly_cutoff=hourly_cutoff,
    )
    if hourly_count >= OTP_MAX_PER_HOUR:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="otp_too_many_requests",
        )

    otp = f"{secrets.randbelow(10_000):04d}"
    otp_hash = _hash_otp(normalized_phone, otp, otp_pepper=otp_pepper)

    if (debug and otp_debug_log_plaintext) or _is_local_request(request):
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

    expires_at = now + timedelta(minutes=otp_ttl_minutes)
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

    if delivery_mode == "local_log_only":
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
        return {"status": "otp_sent", "delivery_channel": "whatsapp"}

    if delivery_mode == "email_only":
        user = auth_repository.get_active_user_by_phone_candidates(
            db,
            phone_candidates=phone_candidates(normalized_phone),
        )
        email = getattr(user, "email", None) if user else None
        if not email:
            # Return generic response to prevent user enumeration (OWASP A07)
            logger.info(
                "otp email_only no email found trace_id=%s phone_last4=%s — returning generic response",
                trace_id,
                _phone_last4(normalized_phone),
            )
            return {"status": "otp_sent", "delivery_channel": "email"}
        try:
            email_result = send_otp_email(to_email=email, otp=otp)
        except Exception:
            row.status = "FAILED"
            db.add(row)
            db.commit()
            logger.exception(
                (
                    "email otp send failed trace_id=%s phone_country_code=%s "
                    "phone_last4=%s otp_request_id=%s mapped_backend_error_code=%s"
                ),
                trace_id,
                country_code,
                _phone_last4(normalized_phone),
                row.id,
                "email_delivery_failed",
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="email_delivery_failed",
            )

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

        row.status = "FAILED"
        db.add(row)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="email_delivery_failed",
        )

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

    user = auth_repository.get_active_user_by_phone_candidates(
        db,
        phone_candidates=phone_candidates(normalized_phone),
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

    # All delivery attempts exhausted — return generic response to prevent enumeration (OWASP A07)
    logger.warning(
        "otp all delivery channels failed trace_id=%s phone_last4=%s — returning generic response",
        trace_id,
        _phone_last4(normalized_phone),
    )
    return {"status": "otp_sent", "delivery_channel": "whatsapp"}


def verify_otp(
    *,
    payload_phone: str,
    payload_otp: str,
    db: Session,
    otp_pepper: str,
    jwt_secret: str,
    jwt_ttl_minutes: int,
) -> dict[str, str]:
    now = datetime.now(timezone.utc)
    normalized_phone = normalize_phone_for_otp(payload_phone)

    otp_row = auth_repository.get_latest_active_otp_request(
        db,
        phone=normalized_phone,
        now=now,
    )
    if not otp_row:
        latest_any = auth_repository.get_latest_unconsumed_otp_request(
            db,
            phone=normalized_phone,
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

    if (otp_row.attempt_count or 0) >= OTP_MAX_VERIFY_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="otp_too_many_attempts",
        )

    expected_hash = otp_row.otp_hash
    provided_hash = _hash_otp(normalized_phone, payload_otp, otp_pepper=otp_pepper)
    if not hmac.compare_digest(expected_hash, provided_hash):
        otp_row.attempt_count = (otp_row.attempt_count or 0) + 1
        db.add(otp_row)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="otp_invalid",
        )

    otp_row.consumed_at = now
    db.add(otp_row)
    db.commit()

    user = auth_repository.get_active_user_by_phone_candidates(
        db,
        phone_candidates=phone_candidates(payload_phone),
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="user_not_found",
        )

    exp = now + timedelta(minutes=jwt_ttl_minutes)
    token_payload = {
        "sub": str(user.id),
        "role": user.role,
        "is_super_admin": normalize_role(user.role) == "SUPER_ADMIN",
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    token = _jwt_encode_hs256(token_payload, jwt_secret=jwt_secret)
    return {"access_token": token, "token_type": "bearer"}


def get_me(*, db: Session, current_user: User) -> dict[str, Any]:
    user_schools = auth_repository.list_user_schools(db, user_id=current_user.id)
    return {
        "id": current_user.id,
        "phone": current_user.phone,
        "role": current_user.role,
        "schools": [
            {
                "id": user_school.school_id,
                "name": user_school.school.name,
                "role": user_school.role,
            }
            for user_school in user_schools
        ],
    }
