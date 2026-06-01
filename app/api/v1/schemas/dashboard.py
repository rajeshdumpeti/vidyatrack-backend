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


class ManagementDashboardSchoolOption(BaseModel):
    id: int
    name: str
    is_selected: bool


class ManagementDashboardKpis(BaseModel):
    total_students: int
    students_growth_pct: float
    fee_collected_mtd: float
    fee_target_pct: float
    fee_pending: float
    fee_overdue_days: int
    total_staff: int
    new_joiners_this_month: int
    avg_attendance_pct: float
    attendance_trend: str


class ManagementDashboardFeeChartItem(BaseModel):
    month: str
    actual: float
    target: float


class ManagementDashboardAlert(BaseModel):
    id: str
    type: str
    severity: str
    title: str
    description: str
    count: int
    school_id: int | None = None
    action_type: str
    created_at: datetime


class ManagementDashboardAlertActionIn(BaseModel):
    alert_type: str
    action_type: str
    school_id: int | None = None


class ManagementDashboardAlertActionOut(BaseModel):
    success: bool
    message: str
    action_logged_at: datetime


class ManagementDashboardAlertHistoryItem(BaseModel):
    event_type: str
    title: str
    description: str
    performed_at: datetime


class ManagementDashboardAlertHistoryOut(BaseModel):
    success: bool
    items: list[ManagementDashboardAlertHistoryItem]


class ManagementDashboardSchoolMatrixRow(BaseModel):
    school_id: int
    school_name: str
    enrollment: int
    collection: float
    attendance_pct: float
    grade: str


class ManagementDashboardQuarterlyOutlook(BaseModel):
    projected_revenue: float
    growth_forecast_pct: float
    target_accomplished_pct: float


class ManagementDashboardActivityItem(BaseModel):
    event_type: str
    description: str
    performed_by: str
    performed_at: datetime


class ManagementDashboardData(BaseModel):
    school_selector: list[ManagementDashboardSchoolOption]
    kpis: ManagementDashboardKpis
    fee_chart: list[ManagementDashboardFeeChartItem]
    alerts: list[ManagementDashboardAlert]
    school_matrix: list[ManagementDashboardSchoolMatrixRow]
    quarterly_outlook: ManagementDashboardQuarterlyOutlook
    recent_activity: list[ManagementDashboardActivityItem]
    principal: PrincipalSummary


class ManagementDashboardOut(BaseModel):
    success: bool
    data: ManagementDashboardData
