from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class UserSchool(Base):
    __tablename__ = "user_schools"

    __table_args__ = (
        # One row per (user, school, role) — allows same person to hold
        # multiple roles at the same school without conflict.
        # e.g. principal + teacher at School A is two separate rows.
        UniqueConstraint("user_id", "school_id", "role", name="uq_user_school_role"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    school_id: Mapped[int] = mapped_column(
        ForeignKey("schools.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Role at this school — lowercase: management | principal | teacher | super_admin
    role: Mapped[str] = mapped_column(String(32), nullable=False)

    # Soft-deactivate a specific role without deleting the user.
    # e.g. when a principal is replaced, their old entry gets is_active=False
    # while they may still have a teacher role that remains active.
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )

    user = relationship("User", backref="school_links")
    school = relationship("School", backref="user_links")
