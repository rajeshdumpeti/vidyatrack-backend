from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MarksRecord(Base):
    __tablename__ = "marks_records"

    __table_args__ = (
        UniqueConstraint(
            "school_id",
            "student_id",
            "subject_id",
            "exam_type",
            name="uq_marks_school_student_subject_exam",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    school_id: Mapped[int] = mapped_column(
        ForeignKey("schools.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"),
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

    marks_obtained: Mapped[int] = mapped_column(nullable=False)
    max_marks: Mapped[int] = mapped_column(nullable=False)

    recorded_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    created_at: Mapped["DateTime"] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
