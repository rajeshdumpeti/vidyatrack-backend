from sqlalchemy import DateTime, ForeignKey, Index, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class StudentNote(Base):
    __tablename__ = "student_notes"

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

    author_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    note_text: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped["DateTime"] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


Index("ix_student_notes_school_student",
      StudentNote.school_id, StudentNote.student_id)
