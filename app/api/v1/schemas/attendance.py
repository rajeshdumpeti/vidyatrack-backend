from datetime import datetime, date as date_type
from typing import Optional

from pydantic import BaseModel, ConfigDict


class AttendanceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    student_id: int
    date: date_type
    status: str
    school_id: Optional[int] = None


class AttendanceOut(BaseModel):
    id: Optional[int] = None
    school_id: int
    student_id: int
    student_name: Optional[str] = None
    section_id: Optional[int] = None
    class_name: Optional[str] = None
    section_name: Optional[str] = None
    date: date_type
    status: str
    marked_by_user_id: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)


class AttendanceSubmitIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    section_id: int
    date: date_type


class AttendanceSubmissionOut(BaseModel):
    id: int
    school_id: int
    section_id: int
    date: date_type
    submitted_by_user_id: int | None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class AttendanceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: str
    student_id: Optional[int] = None
    date: Optional[date_type] = None
