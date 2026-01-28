from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    school_id: Mapped[int | None] = mapped_column(
        ForeignKey("schools.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        default=None
    )

    phone: Mapped[str] = mapped_column(
        String(20), nullable=False, unique=True, index=True)

    email: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True)
    # MVP roles: SUPER_ADMIN | MANAGEMENT | PRINCIPAL | TEACHER
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True)
