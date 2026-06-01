from __future__ import annotations

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class FeeStructure(Base):
    __tablename__ = "fee_structures"
    __table_args__ = (
        UniqueConstraint("school_id", "session", "grade_name",
                         name="uq_fee_structures_school_session_grade"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    school_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("schools.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Human-friendly label; optional but helpful.
    name: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # e.g. "2026-2027"
    session: Mapped[str] = mapped_column(
        String(16), nullable=False, index=True)

    # e.g. "Grade 1", "LKG"
    grade_name: Mapped[str] = mapped_column(
        String(32), nullable=False, index=True)

    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True)

    created_at: Mapped["DateTime"] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
