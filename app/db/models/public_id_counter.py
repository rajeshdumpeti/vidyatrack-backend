import uuid

from sqlalchemy import Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from app.core.uuid import uuid7
from app.db.base import Base


class PublicIdCounter(Base):
    __tablename__ = "public_id_counters"
    __table_args__ = (
        UniqueConstraint("tenant_code", "entity", "year", name="uq_public_id_counter"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid7
    )
    tenant_code: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    entity: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_seq: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
