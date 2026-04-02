from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # nullable — failed attempts may not resolve to a user
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # login_success | login_failure | login_locked | password_reset_requested | password_reset_complete
    event: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # The identifier the user submitted (email or phone) — safe to log
    identifier: Mapped[str | None] = mapped_column(String(255), nullable=True)

    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # web | mobile
    device_type: Mapped[str | None] = mapped_column(String(16), nullable=True)

    browser: Mapped[str | None] = mapped_column(String(128), nullable=True)

    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)

    created_at: Mapped["DateTime"] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
