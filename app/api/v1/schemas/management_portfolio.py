from __future__ import annotations

from pydantic import BaseModel


class ManagementStudentsSummaryOut(BaseModel):
    total_students: int
    girls_count: int
    boys_count: int
    other_gender_count: int
    sections_covered: int
    classes_covered: int
    new_admissions_this_month: int


class ManagementStaffSummaryOut(BaseModel):
    total_teachers: int
    active_teachers: int
    on_leave_teachers: int
    inactive_teachers: int
    teachers_with_primary_section: int
    principal_assigned: bool

