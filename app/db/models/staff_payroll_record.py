from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class StaffPayrollRecord(Base):
    __tablename__ = "staff_payroll_records"

    __table_args__ = (
        UniqueConstraint("school_id", "user_id", "payroll_month", name="uq_staff_payroll_school_user_month"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    payroll_month: Mapped["Date"] = mapped_column(Date, nullable=False, index=True)
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    payment_mode: Mapped[str] = mapped_column(String(32), nullable=False, server_default="bank_transfer")
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="PAID")
    reference_note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    processed_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    processed_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
