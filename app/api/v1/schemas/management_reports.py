from __future__ import annotations

from pydantic import BaseModel


class AttendanceReportRow(BaseModel):
    class_name: str
    present_count: int
    absent_count: int
    attendance_pct: float


class ExamPerformanceRow(BaseModel):
    subject_name: str
    exam_type: str
    avg_marks_pct: float
    pass_rate_pct: float


class FeeCollectionRow(BaseModel):
    month: str
    collected_amount: float
    payment_count: int


class StaffActivityRow(BaseModel):
    name: str
    role: str
    status: str


class ManagementReportsOut(BaseModel):
    success: bool
    data: dict
