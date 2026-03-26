# app/db/models/teacher.py
import uuid

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from app.core.uuid import uuid7
from app.db.base import Base

# Valid teacher statuses — stored as plain strings to avoid Postgres enum migration pain
TEACHER_STATUSES = ("ACTIVE", "ON_LEAVE", "RESIGNED", "TRANSFERRED")


class Teacher(Base):
    __tablename__ = "teachers"

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
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        unique=True,  # pilot: one user maps to one teacher
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # ACTIVE | ON_LEAVE | RESIGNED | TRANSFERRED
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="ACTIVE"
    )
