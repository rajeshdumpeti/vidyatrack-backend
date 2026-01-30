from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class UserSchool(Base):
    __tablename__ = "user_schools"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    school_id: Mapped[int] = mapped_column(
        ForeignKey("schools.id", ondelete="CASCADE"),
        nullable=False
    )

    # We store the role here because a user might be
    # 'management' in School A but 'teacher' in School B
    role: Mapped[str] = mapped_column(String(32), nullable=False)

    # Relationships for easier querying later
    user = relationship("User", backref="school_links")
    school = relationship("School", backref="user_links")
