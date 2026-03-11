from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SchoolCreate(BaseModel):
    name: str
    school_code: str | None = None
    admin_phone: str
    admin_email: str | None = None


class SchoolOut(BaseModel):
    id: int
    public_id: str
    name: str
    code: str | None = None
    board: str | None = None
    category: str | None = None
    medium: str | None = None
    school_type: str | None = None
    established_year: int | None = None
    affiliation_number: str | None = None
    udise_code: str | None = None
    status: str
    created_by: int | None = None
    updated_by: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    teacher_count: int = 0
    student_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class SchoolDashboardOut(BaseModel):
    school_id: int
    school_public_id: str | None = None
    teacher_count: int
    student_count: int
    staff_count: int
    total_registered: int


class SchoolTeacherListItem(BaseModel):
    id: int
    school_id: int
    name: str
    email: str | None = None
    phone: str | None = None
    status: str = "active"


class SchoolStudentListItem(BaseModel):
    id: int
    school_id: int
    name: str
    parent_name: str | None = None
    parent_phone: str | None = None
    status: str = "active"


class SchoolStaffListItem(BaseModel):
    user_id: int
    school_id: int
    role: str
    name: str
    email: str | None = None
    phone: str | None = None
    status: str = "active"
