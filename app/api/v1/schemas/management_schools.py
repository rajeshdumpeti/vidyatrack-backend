from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ManagementSchoolsSummaryOut(BaseModel):
    total_schools: int
    total_students: int
    total_staff: int
    monthly_collection: float
    pending_collection: float


class ManagementSchoolOverviewItemOut(BaseModel):
    school_id: int
    school_name: str
    school_code: str | None = None
    status: str
    board: str | None = None
    category: str | None = None
    current_session: str | None = None
    city: str | None = None
    state: str | None = None
    principal_name: str | None = None
    student_count: int
    teacher_count: int
    staff_count: int
    attendance_pct: float
    fee_collected_mtd: float
    fee_pending: float
    setup_completion_pct: int
    modules_enabled: list[str]
    last_activity_at: datetime | None = None


class ManagementSchoolsOverviewDataOut(BaseModel):
    summary: ManagementSchoolsSummaryOut
    schools: list[ManagementSchoolOverviewItemOut]


class ManagementSchoolsOverviewOut(BaseModel):
    success: bool
    data: ManagementSchoolsOverviewDataOut
