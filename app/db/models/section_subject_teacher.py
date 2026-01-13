from sqlalchemy import DateTime, ForeignKey, Index, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SectionSubjectTeacher(Base):
    __tablename__ = "section_subject_teachers"

    __table_args__ = (
        UniqueConstraint(
            "school_id",
            "section_id",
            "subject_id",
            name="uq_sst_school_section_subject",
        ),
        Index("ix_sst_school_section", "school_id", "section_id"),
        Index("ix_sst_school_teacher", "school_id", "teacher_id"),
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

    teacher_id: Mapped[int] = mapped_column(
        ForeignKey("teachers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    created_at: Mapped["DateTime"] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
