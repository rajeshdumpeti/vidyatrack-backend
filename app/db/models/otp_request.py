from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class OtpRequest(Base):
    __tablename__ = "otp_requests"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    phone: Mapped[str] = mapped_column(String(20), nullable=False, index=True)

    # Store hash only, never store the raw OTP
    otp_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    expires_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), nullable=False)

    attempt_count: Mapped[int] = mapped_column(nullable=False, default=0)

    # login | password_reset | login_2fa
    purpose: Mapped[str] = mapped_column(String(32), nullable=False, default="login")

    channel: Mapped[str] = mapped_column(String(16), nullable=False, default="WHATSAPP")

    provider_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    status: Mapped[str] = mapped_column(String(16), nullable=False, default="PENDING")

    attempts: Mapped[int] = mapped_column(nullable=False, default=0)

    sent_at: Mapped["DateTime | None"] = mapped_column(DateTime(timezone=True), nullable=True)

    consumed_at: Mapped["DateTime | None"] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped["DateTime"] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
