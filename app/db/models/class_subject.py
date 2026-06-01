import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.uuid import uuid7
from app.db.base import Base


class ClassSubject(Base):
    __tablename__ = "class_subjects"
    __table_args__ = (
        UniqueConstraint(
            "school_id",
            "class_id",
            "subject_id",
            name="uq_class_subjects_school_class_subject",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    internal_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), unique=True, nullable=False, default=uuid7
    )
    public_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    school_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("schools.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    class_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("classes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    subject_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("subjects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    subject_type: Mapped[str] = mapped_column(String(24), nullable=False, default="core")
    max_marks: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    passing_marks: Mapped[int] = mapped_column(Integer, nullable=False, default=35)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
