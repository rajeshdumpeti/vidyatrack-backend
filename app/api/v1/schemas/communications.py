from datetime import date, datetime
from typing import List

from pydantic import BaseModel, ConfigDict, Field


class HomeworkCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    section_id: int
    subject_id: int
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1)
    due_date: date | None = None


class HomeworkOut(BaseModel):
    id: int
    school_id: int
    section_id: int
    subject_id: int
    title: str
    description: str
    due_date: date | None
    created_by: int | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ParentMessageCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    section_id: int
    student_ids: List[int] = Field(min_length=1)
    message: str = Field(min_length=1)
    subject: str | None = Field(default=None, max_length=200)


class ParentMessageOut(BaseModel):
    id: int
    message_id: int
    school_id: int
    section_id: int
    subject: str | None = None
    message: str
    student_ids: List[int]
    delivered_count: int
    created_by: int | None
    created_at: datetime
