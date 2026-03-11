from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class DashboardNotice(BaseModel):
    id: str
    title: str
    message: str
    created_at: datetime
    kind: str


class PrincipalSummary(BaseModel):
    assigned: bool
    principal_id: int | None = None
    name: str | None = None


class PrincipalDashboardOut(BaseModel):
    total_students: int
    total_teachers: int
    attendance_today_pct: float
    attendance_today_present: int
    attendance_today_absent: int
    attendance_today_total: int
    notices: list[DashboardNotice]


class ManagementDashboardOut(BaseModel):
    total_students: int
    total_teachers: int
    attendance_today_pct: float
    attendance_today_present: int
    attendance_today_absent: int
    attendance_today_total: int
    principal: PrincipalSummary
    notices: list[DashboardNotice]
