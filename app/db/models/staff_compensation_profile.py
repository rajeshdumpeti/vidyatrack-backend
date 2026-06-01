from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class StaffCompensationProfile(Base):
    __tablename__ = "staff_compensation_profiles"

    __table_args__ = (
        UniqueConstraint("school_id", "user_id", name="uq_staff_compensation_school_user"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    employment_type: Mapped[str] = mapped_column(String(32), nullable=False, server_default="permanent")
    gross_salary: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, server_default="0")
    payment_day: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    payment_mode: Mapped[str] = mapped_column(String(32), nullable=False, server_default="bank_transfer")
    date_of_joining: Mapped["Date | None"] = mapped_column(Date, nullable=True)
    contract_end_date: Mapped["Date | None"] = mapped_column(Date, nullable=True)
    created_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
