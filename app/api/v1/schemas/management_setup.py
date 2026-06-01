from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ManagementSetupStepOut(BaseModel):
    key: str
    label: str
    completed: bool
    count: int | None = None
    required_min: int = 1


class ManagementSetupStatusOut(BaseModel):
    school_id: int
    management_setup_complete: bool
    management_setup_completed_at: str | None = None
    completion_pct: int
    completed_steps: int
    total_steps: int
    steps: list[ManagementSetupStepOut]


class ManagementSetupCompleteOut(BaseModel):
    success: bool
    management_setup_complete: bool
    completed_at: str


class ManagementSchoolProfileOut(BaseModel):
    school_id: int
    school_name: str
    school_code: str | None = None
    board: str | None = None
    category: str | None = None
    medium: str | None = None
    school_type: str | None = None
    established_year: int | None = None
    current_session: str | None = None
    working_days_per_week: int | None = None
    academic_start_month: int | None = None
    academic_end_month: int | None = None
    class_levels: list[str] = []
    street: str | None = None
    area: str | None = None
    city: str | None = None
    district: str | None = None
    state: str | None = None
    pin_code: str | None = None
    country: str | None = None
    landmark: str | None = None
    school_phone: str | None = None
    school_email: str | None = None
    website: str | None = None
    modules_enabled: list[str] = []


class ManagementSchoolProfileUpdateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    board: str | None = Field(default=None, max_length=64)
    category: str | None = Field(default=None, max_length=64)
    medium: str | None = Field(default=None, max_length=64)
    school_type: str | None = Field(default=None, max_length=64)
    established_year: int | None = Field(default=None, ge=1800, le=2100)
    current_session: str | None = Field(default=None, max_length=64)
    working_days_per_week: int | None = Field(default=None, ge=1, le=7)
    academic_start_month: int | None = Field(default=None, ge=1, le=12)
    academic_end_month: int | None = Field(default=None, ge=1, le=12)
    class_levels: list[str] = Field(default_factory=list)
    street: str | None = Field(default=None, max_length=255)
    area: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=128)
    district: str | None = Field(default=None, max_length=128)
    state: str | None = Field(default=None, max_length=128)
    pin_code: str | None = Field(default=None, max_length=12)
    country: str | None = Field(default=None, max_length=128)
    landmark: str | None = Field(default=None, max_length=255)
    school_phone: str | None = Field(default=None, max_length=20)
    school_email: str | None = Field(default=None, max_length=255)
    website: str | None = Field(default=None, max_length=255)


class ManagementSectionCreateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    class_id: int
    name: str = Field(min_length=1, max_length=50)
    capacity: int = Field(default=40, ge=1, le=500)
    room_number: str | None = Field(default=None, max_length=20)


class ManagementSectionOut(BaseModel):
    id: int
    public_id: str
    school_id: int
    class_id: int
    class_name: str
    name: str
    capacity: int
    room_number: str | None = None
    is_active: bool


class ManagementSectionGroupOut(BaseModel):
    class_id: int
    class_name: str
    sections: list[ManagementSectionOut]


class ManagementClassSubjectCreateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    class_id: int
    subject_id: int | None = None
    name: str | None = Field(default=None, max_length=255)
    subject_type: Literal["core", "elective", "language", "activity"] = "core"
    max_marks: int = Field(default=100, ge=1, le=1000)
    passing_marks: int = Field(default=35, ge=0, le=1000)


class ManagementClassSubjectOut(BaseModel):
    id: int
    public_id: str
    class_id: int
    class_name: str
    subject_id: int
    subject_name: str
    subject_type: str
    max_marks: int
    passing_marks: int
    is_active: bool


class ManagementClassSubjectsResponse(BaseModel):
    class_id: int
    class_name: str
    subjects: list[ManagementClassSubjectOut]
    subject_catalog: list[dict[str, int | str]]
