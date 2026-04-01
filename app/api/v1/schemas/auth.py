from typing import Any
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Existing OTP schemas (unchanged)
# ---------------------------------------------------------------------------

class OtpRequestIn(BaseModel):
    phone: str


class OtpRequestOut(BaseModel):
    status: str
    delivery_channel: str


class OtpVerifyIn(BaseModel):
    phone: str
    otp: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RoleOption(BaseModel):
    """One available (school, role) combination for a multi-role user."""
    school_id: int
    school_name: str
    role: str  # lowercase: management | principal | teacher


class OtpVerifyOut(BaseModel):
    """
    Extended OTP verify response.
    Backward-compatible with TokenOut — access_token is always present.
    If requires_role_selection is True the client should present a role
    picker and call POST /auth/select-role to obtain a role-scoped JWT.
    """
    access_token: str
    token_type: str = "bearer"
    requires_role_selection: bool = False
    available_roles: list[RoleOption] = []


class SelectRoleIn(BaseModel):
    school_id: int
    role: str  # e.g. "principal", "teacher", "management"


# ---------------------------------------------------------------------------
# Password login schemas
# ---------------------------------------------------------------------------

class DeviceInfoIn(BaseModel):
    device_type: str = "web"   # web | mobile
    browser: str | None = None
    user_agent: str | None = None
    # ip_address is intentionally excluded — captured server-side only


class PasswordLoginIn(BaseModel):
    identifier: str          # email or 10-digit phone
    password: str
    remember_me: bool = False
    login_method: str = "password"   # password | otp
    device_info: DeviceInfoIn = DeviceInfoIn()


class Verify2FAIn(BaseModel):
    two_fa_token: str
    otp: str
    remember_me: bool = False


class RefreshTokenIn(BaseModel):
    refresh_token: str


# ---------------------------------------------------------------------------
# Password reset schemas
# ---------------------------------------------------------------------------

class ForgotPasswordIn(BaseModel):
    identifier: str   # email or phone — auto-detected


class VerifyResetOtpIn(BaseModel):
    phone: str        # phone or email used for recovery
    otp: str          # 6 digits
    purpose: str = "password_reset"   # password_reset


class ResetPasswordIn(BaseModel):
    reset_token: str
    new_password: str
    confirm_password: str
