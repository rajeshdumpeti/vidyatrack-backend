from datetime import datetime

from pydantic import BaseModel, ConfigDict


class StudentNoteCreate(BaseModel):
    note_text: str
    section_id: int | None = None
    subject_id: int | None = None
    model_config = ConfigDict(extra="forbid")


class StudentNoteOut(BaseModel):
    id: int
    school_id: int
    student_id: int
    student_name: str | None = None
    section_id: int | None = None
    subject_id: int | None = None
    author_user_id: int | None
    author_name: str | None = None
    author_role: str | None = None
    class_name: str | None = None
    section_name: str | None = None
    subject_name: str | None = None
    note_text: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
