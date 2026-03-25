import logging

from app.core.config import settings
from app.core.phone import to_e164
from app.db.models.user import User
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)


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
        existing = (
            db.query(User)
            .filter(User.role == "SUPER_ADMIN", User.is_active == True)
            .first()
        )
        if existing:
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
