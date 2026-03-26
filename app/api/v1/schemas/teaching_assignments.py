from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TeachingAssignmentCreate(BaseModel):
    section_id: int
    subject_id: int
    teacher_id: int
    school_id: int


class TeachingAssignmentOut(BaseModel):
    id: int
    school_id: int
    section_id: int
    subject_id: int
    teacher_id: int
    substitute_teacher_id: int | None = None

    model_config = ConfigDict(from_attributes=True)


class SetSubstitutePayload(BaseModel):
    substitute_teacher_id: int | None


class TeacherAssignmentHistoryOut(BaseModel):
    id: int
    school_id: int
    section_id: int
    subject_id: int
    previous_teacher_id: int | None
    new_teacher_id: int
    changed_by_user_id: int | None
    action: str
    changed_at: datetime

    model_config = ConfigDict(from_attributes=True)
