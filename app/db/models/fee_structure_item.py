from __future__ import annotations

from sqlalchemy import DateTime, ForeignKey, Integer, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class FeeStructureItem(Base):
    __tablename__ = "fee_structure_items"
    __table_args__ = (
        UniqueConstraint("fee_structure_id", "fee_head_id", name="uq_fee_structure_items_structure_head"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    fee_structure_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("fee_structures.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    fee_head_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("fee_heads.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Amount in INR rupees (integer) for MVP.
    amount: Mapped[int] = mapped_column(Integer, nullable=False)

    created_at: Mapped["DateTime"] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

