from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.phone import normalize_phone_for_otp


class ManagementPrincipalIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    school_id: int = Field(gt=0)
    name: str = Field(min_length=1, max_length=200)
    phone: str = Field(min_length=10, max_length=20)
    email: str | None = Field(default=None, min_length=5, max_length=255)

    @model_validator(mode="after")
    def normalize(self) -> "ManagementPrincipalIn":
        self.phone = normalize_phone_for_otp(self.phone)
        if self.email is not None:
            self.email = self.email.strip()
            if self.email == "":
                self.email = None
        self.name = self.name.strip()
        return self


class ManagementPrincipalOut(BaseModel):
    principal_id: int
    principal_public_id: str
    user_id: int
    name: str
    phone: str
    email: str | None = None


class ManagementPrincipalRegisterOut(BaseModel):
    status: str
    principal: ManagementPrincipalOut
    otp_status: str
    delivery_channel: str | None = None
    otp_error_code: str | None = None
    message: str


class ManagementPrincipalOtpRetryOut(BaseModel):
    status: str
    delivery_channel: str | None = None
    otp_error_code: str | None = None
    message: str


class PrincipalHistoryOut(BaseModel):
    id: int
    name: str
    phone: str
    email: str | None = None
    status: str
    assigned_at: datetime
    deactivated_at: datetime | None = None


class PrincipalOnboardingStartOut(BaseModel):
    status: str
    session_id: int
    phone_masked: str
    expires_at: datetime
    delivery_channel: str | None = None
    message: str


class PrincipalOnboardingResendIn(BaseModel):
    school_id: int = Field(gt=0)
    session_id: int = Field(gt=0)


class PrincipalOnboardingVerifyIn(BaseModel):
    school_id: int = Field(gt=0)
    session_id: int = Field(gt=0)
    otp: str = Field(min_length=4, max_length=8)


class PrincipalOnboardingVerifyOut(BaseModel):
    status: str
    principal: ManagementPrincipalOut
    deactivated_principals: list[PrincipalHistoryOut]
    message: str
