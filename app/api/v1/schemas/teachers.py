from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

TeacherStatus = Literal["ACTIVE", "ON_LEAVE", "RESIGNED", "TRANSFERRED"]


class TeacherStatusUpdate(BaseModel):
    status: TeacherStatus


class TeacherCreate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str
    phone: str = Field(min_length=10, max_length=20)
    email: Optional[str] = None
    school_id: int
    section_id: Optional[int] = None


class TeacherOut(BaseModel):
    id: int
    public_id: str
    school_id: int
    user_id: Optional[int] = None
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    employee_id: Optional[str] = None
    status: Optional[str] = None
    assigned_section_label: Optional[str] = None
    assignments: list[dict] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True)
