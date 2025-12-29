from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class NotificationOutbox(Base):
    __tablename__ = "notification_outbox"

    __table_args__ = (
        UniqueConstraint("submission_id", "student_id", "channel",
                         name="uq_outbox_submission_student_channel"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    submission_id: Mapped[int] = mapped_column(
        ForeignKey("attendance_submissions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    channel: Mapped[str] = mapped_column(String(32), nullable=False)

    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending")

    created_at: Mapped["DateTime"] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
