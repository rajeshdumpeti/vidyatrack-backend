from sqlalchemy import DateTime, Integer, JSON, String, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SchoolOnboardingDraft(Base):
    __tablename__ = "school_onboarding_drafts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, index=True)

    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")

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
