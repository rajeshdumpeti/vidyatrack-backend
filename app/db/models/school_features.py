from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SchoolFeatures(Base):
    __tablename__ = "school_features"
    __table_args__ = (
        UniqueConstraint("school_id", name="uq_school_features_school_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    school_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("schools.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    modules_enabled: Mapped[list | None] = mapped_column(JSON, nullable=True)
    max_students: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_teachers: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_staff: Mapped[int | None] = mapped_column(Integer, nullable=True)
    storage_limit_gb: Mapped[int | None] = mapped_column(Integer, nullable=True)

    api_access: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    bulk_operations: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    custom_reports: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notification_preferences: Mapped[dict | None] = mapped_column(JSON, nullable=True)

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
