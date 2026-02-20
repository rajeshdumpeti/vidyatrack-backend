from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SchoolAcademicDetails(Base):
    __tablename__ = "school_academic_details"
    __table_args__ = (
        UniqueConstraint("school_id", name="uq_school_academic_details_school_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    school_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("schools.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    current_session: Mapped[str | None] = mapped_column(String(64), nullable=True)
    academic_start_month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    academic_end_month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    working_days_per_week: Mapped[int | None] = mapped_column(Integer, nullable=True)
    class_levels: Mapped[list | None] = mapped_column(JSON, nullable=True)

    lkg_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ukg_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    pre_nursery_available: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
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
