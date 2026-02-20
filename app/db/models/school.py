from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class School(Base):
    """
    Represents a school tenant in VidyaTrack.

    This is the top-level entity required for multi-tenant separation.
    """
    __tablename__ = "schools"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    code: Mapped[str | None] = mapped_column(
        String(64), nullable=True, unique=True, index=True
    )
    board: Mapped[str | None] = mapped_column(String(64), nullable=True)
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    medium: Mapped[str | None] = mapped_column(String(64), nullable=True)
    school_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    established_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    affiliation_number: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )
    udise_code: Mapped[str | None] = mapped_column(
        String(32), nullable=True, unique=True, index=True
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="ACTIVE"
    )

    created_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped["DateTime"] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped["DateTime"] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
