from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel


class ManagementStaffListItem(BaseModel):
    user_id: int
    role: str
    name: str
    employee_id: str
    school_name: str
    join_date: date | None = None
    monthly_salary: float
    employment_type: str | None = None
    payment_mode: str | None = None
    payroll_status: str
    contract_end_date: date | None = None


class ManagementStaffListOut(BaseModel):
    items: list[ManagementStaffListItem]
    total: int


class ManagementStaffStatsOut(BaseModel):
    monthly_payroll: float
    active_staff: int
    pending_payouts: int
    next_pay_date: date
    composition: dict[str, float]
    contracts_expiring_soon: int


class ManagementStaffCompensationUpdateIn(BaseModel):
    gross_salary: float
    employment_type: str = "permanent"
    payment_mode: str = "bank_transfer"
    payment_day: int = 1
    date_of_joining: date | None = None
    contract_end_date: date | None = None


class ManagementStaffPayrollProcessIn(BaseModel):
    school_id: int | None = None
    user_id: int | None = None
    payroll_month: date | None = None
    reference_note: str | None = None


class ManagementStaffPayrollProcessOut(BaseModel):
    success: bool
    processed_count: int
    payroll_month: date
    processed_at: datetime
