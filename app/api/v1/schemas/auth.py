from pydantic import BaseModel


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
