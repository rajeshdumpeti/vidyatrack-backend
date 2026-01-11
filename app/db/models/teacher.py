# app/db/models/teacher.py
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Teacher(Base):
    __tablename__ = "teachers"

    id: Mapped[int] = mapped_column(primary_key=True)
    school_id: Mapped[int] = mapped_column(
        ForeignKey("schools.id"), nullable=False)

    user_id: Mapped[int] = mapped_column(   # ✅ ADD THIS
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        unique=True,   # one user = one teacher (pilot)
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
