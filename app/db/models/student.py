import uuid

from sqlalchemy import Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from app.core.uuid import uuid7
from app.db.base import Base


class Student(Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    internal_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), unique=True, nullable=False, default=uuid7
    )
    public_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)

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
    first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    date_of_birth: Mapped["Date | None"] = mapped_column(Date, nullable=True)
    gender: Mapped[str | None] = mapped_column(String(16), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="ACTIVE")
    academic_year: Mapped[str | None] = mapped_column(String(32), nullable=True)
    roll_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    admission_date: Mapped["Date | None"] = mapped_column(Date, nullable=True)
    admission_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    blood_group: Mapped[str | None] = mapped_column(String(8), nullable=True)
    nationality: Mapped[str | None] = mapped_column(String(64), nullable=True)
    religion: Mapped[str | None] = mapped_column(String(64), nullable=True)
    caste_category: Mapped[str | None] = mapped_column(String(32), nullable=True)
    mother_tongue: Mapped[str | None] = mapped_column(String(64), nullable=True)
    aadhaar_number: Mapped[str | None] = mapped_column(String(255), nullable=True)
    birth_cert_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    previous_school_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    previous_school_tc_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)

    parent_phone: Mapped[str] = mapped_column(String(32), nullable=False)
    parent_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    emergency_contact_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    emergency_contact_relation: Mapped[str | None] = mapped_column(String(64), nullable=True)
    emergency_contact_phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
