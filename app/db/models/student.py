from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Student(Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    school_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("schools.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    section_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("sections.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    parent_phone: Mapped[str] = mapped_column(String(32), nullable=False)
    parent_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
