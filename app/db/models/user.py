from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # school_id: Mapped[int | None] = mapped_column(
    #     ForeignKey("schools.id", ondelete="CASCADE"),
    #     nullable=True,
    #     index=True,
    #     default=None
    # )

    phone: Mapped[str] = mapped_column(
        String(20), nullable=False, unique=True, index=True)

    email: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True)

    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # MVP roles: super_admin | management | principal | teacher
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True)

    # Password-based auth (nullable — OTP-only users have no password)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    locked_until: Mapped["DateTime | None"] = mapped_column(DateTime(timezone=True), nullable=True)
    is_first_login: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_login_at: Mapped["DateTime | None"] = mapped_column(DateTime(timezone=True), nullable=True)

    # Optional permissions/quota for platform admins (nullable for legacy)
    can_create_school: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    max_schools: Mapped[int | None] = mapped_column(
        Integer, nullable=True, default=None
    )
