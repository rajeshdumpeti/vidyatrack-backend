from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MarksSubmission(Base):
    __tablename__ = "marks_submissions"

    __table_args__ = (
        UniqueConstraint(
            "school_id",
            "section_id",
            "subject_id",
            "exam_type",
            name="uq_marks_sub_school_section_subject_exam",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    school_id: Mapped[int] = mapped_column(
        ForeignKey("schools.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    section_id: Mapped[int] = mapped_column(
        ForeignKey("sections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    subject_id: Mapped[int] = mapped_column(
        ForeignKey("subjects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    exam_type: Mapped[str] = mapped_column(
        String(32), nullable=False, index=True)

    submitted_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="submitted")

    created_at: Mapped["DateTime"] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
