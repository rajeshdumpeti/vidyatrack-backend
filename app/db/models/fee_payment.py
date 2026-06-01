from __future__ import annotations

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class FeePayment(Base):
    __tablename__ = "fee_payments"
    __table_args__ = (
        UniqueConstraint("school_id", "receipt_number", name="uq_fee_payments_school_receipt_number"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    school_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("schools.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    student_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("students.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    fee_structure_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("fee_structures.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # e.g. "2026-2027"
    session: Mapped[str] = mapped_column(String(16), nullable=False, index=True)

    amount_paid: Mapped[int] = mapped_column(Integer, nullable=False)
    payment_mode: Mapped[str] = mapped_column(String(20), nullable=False)  # cash|upi|bank_transfer|cheque
    payment_date: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), nullable=False)

    receipt_number: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)

    recorded_by_user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    created_at: Mapped["DateTime"] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    items: Mapped[list["FeePaymentItem"]] = relationship(
        "FeePaymentItem",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class FeePaymentItem(Base):
    __tablename__ = "fee_payment_items"
    __table_args__ = (
        UniqueConstraint("payment_id", "fee_head_id", name="uq_fee_payment_items_payment_head"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    payment_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("fee_payments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    fee_head_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("fee_heads.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped["DateTime"] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

