import logging

from sqlalchemy import func

from app.core.config import settings
from app.core.phone import to_e164
from app.db.models.user import User
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)


def _hash_password(password: str) -> str:
    import bcrypt
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def seed_super_admin() -> None:
    """
    Ensure one super admin exists in the database.

    Reads SUPER_ADMIN_PHONE and SUPER_ADMIN_EMAIL from environment variables.
    Runs on every app startup but only creates the user if none exists yet —
    safe to call repeatedly.
    """
    if not settings.super_admin_phone:
        logger.info("SUPER_ADMIN_PHONE not set — skipping super admin seed")
        return

    try:
        canonical_phone = to_e164(settings.super_admin_phone)
    except ValueError:
        logger.error(
            "SUPER_ADMIN_PHONE '%s' is not a valid phone number — skipping seed",
            settings.super_admin_phone,
        )
        return

    db = SessionLocal()
    try:
        # Prefer looking up by the canonical phone — avoids role-case mismatches in existing DBs.
        existing = (
            db.query(User)
            .filter(User.phone == canonical_phone, User.is_active == True)
            .first()
        )
        if not existing:
            existing = (
                db.query(User)
                .filter(func.lower(User.role) == "super_admin", User.is_active == True)
                .first()
            )
        if existing:
            if settings.super_admin_password and not existing.password_hash:
                existing.password_hash = _hash_password(settings.super_admin_password)
                if (existing.role or "").upper() != "SUPER_ADMIN":
                    existing.role = "SUPER_ADMIN"
                db.add(existing)
                db.commit()
                logger.info("Super admin password initialized from SUPER_ADMIN_PASSWORD")
            else:
                logger.info("Super admin already exists — skipping seed")
            return

        admin = User(
            phone=canonical_phone,
            email=settings.super_admin_email,
            role="SUPER_ADMIN",
            is_active=True,
            can_create_school=True,
            max_schools=None,
        )
        if settings.super_admin_password:
            admin.password_hash = _hash_password(settings.super_admin_password)
        db.add(admin)
        db.commit()
        logger.info(
            "Super admin created",
            extra={"phone": canonical_phone},
        )
    except Exception:
        db.rollback()
        logger.exception("Failed to seed super admin")
    finally:
        db.close()
