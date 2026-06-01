from __future__ import annotations

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SchoolGrade(Base):
    """
    PRD: school_grades table (auto-created by Super Admin wizard).

    This is separate from `Class` (which is used elsewhere in the app).
    """

    __tablename__ = "school_grades"
    __table_args__ = (
        UniqueConstraint("school_id", "grade_code", name="uq_school_grades_school_grade_code"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    school_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("schools.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    grade_name: Mapped[str] = mapped_column(String(50), nullable=False)
    grade_code: Mapped[str] = mapped_column(String(20), nullable=False)
    grade_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped["DateTime"] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

