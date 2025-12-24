from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class School(Base):
    """
    Represents a school tenant in VidyaTrack.

    This is the top-level entity required for multi-tenant separation.
    """
    __tablename__ = "schools"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
