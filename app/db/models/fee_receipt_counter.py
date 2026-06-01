from __future__ import annotations

from sqlalchemy import DateTime, ForeignKey, Integer, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class FeeReceiptCounter(Base):
    """
    Concurrency-safe receipt numbering per school + year.

    Receipt format: RCP-{year}-{seq:04d}
    """

    __tablename__ = "fee_receipt_counters"
    __table_args__ = (
        UniqueConstraint("school_id", "year", name="uq_fee_receipt_counters_school_year"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    school_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("schools.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    next_seq: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    created_at: Mapped["DateTime"] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped["DateTime"] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

