from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class NotificationOutbox(Base):
    __tablename__ = "notification_outbox"

    __table_args__ = (
        # Exactly one submission reference must be set (attendance OR marks)
        CheckConstraint(
            "(attendance_submission_id IS NOT NULL AND marks_submission_id IS NULL) OR "
            "(attendance_submission_id IS NULL AND marks_submission_id IS NOT NULL)",
            name="ck_outbox_exactly_one_submission_fk",
        ),
        # Dedupe for attendance submissions
        Index(
            "uq_outbox_attendance_dedupe",
            "event_type",
            "attendance_submission_id",
            "recipient_phone",
            unique=True,
            postgresql_where="attendance_submission_id IS NOT NULL",
        ),
        # Dedupe for marks submissions
        Index(
            "uq_outbox_marks_dedupe",
            "event_type",
            "marks_submission_id",
            "recipient_phone",
            unique=True,
            postgresql_where="marks_submission_id IS NOT NULL",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    school_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("schools.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    event_type: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True)
    # event_type examples: ATTENDANCE_SUBMITTED, MARKS_SUBMITTED

    attendance_submission_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("attendance_submissions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    marks_submission_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("marks_submissions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    recipient_phone: Mapped[str] = mapped_column(
        String(32), nullable=False, index=True)

    # Minimal payload storage for Phase 1 (stringified JSON or text)
    payload: Mapped[str] = mapped_column(Text, nullable=False)

    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="PENDING", index=True)
    # PENDING | SENT | FAILED

    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped["DateTime"] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    next_attempt_at: Mapped["DateTime"] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )
    sent_at: Mapped["DateTime | None"] = mapped_column(
        DateTime(timezone=True), nullable=True)
