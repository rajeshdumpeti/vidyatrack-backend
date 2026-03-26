from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TeacherAssignmentHistory(Base):
    __tablename__ = "teacher_assignment_history"

    __table_args__ = (
        Index("ix_tah_school_section_subject", "school_id", "section_id", "subject_id"),
        Index("ix_tah_changed_at", "changed_at"),
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
    )
    subject_id: Mapped[int] = mapped_column(
        ForeignKey("subjects.id", ondelete="CASCADE"),
        nullable=False,
    )
    # NULL means this was the very first assignment
    previous_teacher_id: Mapped[int | None] = mapped_column(
        ForeignKey("teachers.id", ondelete="SET NULL"),
        nullable=True,
    )
    new_teacher_id: Mapped[int] = mapped_column(
        ForeignKey("teachers.id", ondelete="CASCADE"),
        nullable=False,
    )
    # who made the change (management user)
    changed_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    # ASSIGNED = first time, REASSIGNED = replacing existing teacher
    action: Mapped[str] = mapped_column(String(20), nullable=False, default="ASSIGNED")

    changed_at: Mapped["DateTime"] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
