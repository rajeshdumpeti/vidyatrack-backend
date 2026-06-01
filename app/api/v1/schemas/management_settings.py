from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class NotificationPreferenceOut(BaseModel):
    fee_overdue: bool = True
    attendance_drop: bool = True
    staff_appraisal: bool = True
    principal_updates: bool = True


class NotificationPreferenceUpdateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fee_overdue: bool
    attendance_drop: bool
    staff_appraisal: bool
    principal_updates: bool


class ManagedUserPasswordResetOut(BaseModel):
    success: bool
    user_id: int
    role: str
    full_name: str | None = None
    login_phone: str | None = None
    login_email: str | None = None
    temp_password: str
