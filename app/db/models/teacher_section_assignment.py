from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, UniqueConstraint, DateTime
from sqlalchemy.sql import func
from app.db.base import Base


class TeacherSectionAssignment(Base):
    __tablename__ = "teacher_section_assignments"

    id = Column(Integer, primary_key=True, index=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False)
    teacher_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    section_id = Column(Integer, ForeignKey("sections.id"), nullable=False)
    subject_name = Column(String(100))  # e.g., 'Telugu'
    is_primary_teacher = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Industry standard: Ensure one teacher isn't assigned the same subject/section twice
    __table_args__ = (
        UniqueConstraint('teacher_user_id', 'section_id',
                         'subject_name', name='uq_teacher_section_subject'),
    )
