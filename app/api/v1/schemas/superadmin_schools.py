from __future__ import annotations

import re
from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.phone import normalize_phone

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PIN_RE = re.compile(r"^\d{6}$")


class SchoolIdentityIn(BaseModel):
    model_config = ConfigDict(extra="ignore")

    school_name: str = Field(min_length=3, max_length=200)
    school_code: str | None = Field(default=None, max_length=20)
    board: str
    category: str
    medium: str
    school_type: str
    established_year: int | None = Field(default=None, ge=1800)
    affiliation_number: str | None = None
    udise_code: str | None = None

    @field_validator("school_name", mode="before")
    @classmethod
    def strip_name(cls, v: str) -> str:
        return v.strip()

    @field_validator("school_code", mode="before")
    @classmethod
    def normalize_code(cls, v: str | None) -> str | None:
        if v is None:
            return None
        cleaned = v.strip().upper()
        return cleaned or None


class LocationContactIn(BaseModel):
    model_config = ConfigDict(extra="ignore")

    street_address: str = Field(min_length=3, max_length=255)
    area: str | None = Field(default=None, max_length=200)
    city: str = Field(min_length=1, max_length=100)
    district: str = Field(min_length=1, max_length=100)
    state: str = Field(min_length=1, max_length=100)
    pincode: str = Field(min_length=6, max_length=6)
    country: str = Field(default="India", max_length=50)
    landmark: str | None = Field(default=None, max_length=200)
    latitude: float | None = None
    longitude: float | None = None
    school_phone: str
    school_email: str
    website: str | None = None

    @field_validator("pincode")
    @classmethod
    def validate_pin(cls, v: str) -> str:
        digits = re.sub(r"\D", "", v)
        if not PIN_RE.match(digits):
            raise ValueError("INVALID_PINCODE")
        return digits

    @field_validator("school_phone", mode="before")
    @classmethod
    def normalize_phone_field(cls, v: str) -> str:
        try:
            return normalize_phone(v)
        except ValueError:
            raise ValueError("INVALID_SCHOOL_PHONE")

    @field_validator("school_email", mode="before")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not EMAIL_RE.match(v):
            raise ValueError("INVALID_SCHOOL_EMAIL")
        return v


class ManagementAdminIn(BaseModel):
    model_config = ConfigDict(extra="ignore")

    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    designation: str | None = Field(default=None, max_length=100)
    department: str | None = Field(default=None, max_length=100)
    employee_id: str | None = Field(default=None, max_length=50)
    phone: str
    email: str
    language: str = Field(default="en", max_length=10)
    timezone: str = Field(default="Asia/Kolkata", max_length=50)
    send_credentials_via: Literal["sms", "email", "both"] = "sms"

    @field_validator("phone", mode="before")
    @classmethod
    def normalize_admin_phone(cls, v: str) -> str:
        try:
            return normalize_phone(v)
        except ValueError:
            raise ValueError("INVALID_ADMIN_PHONE")

    @field_validator("email", mode="before")
    @classmethod
    def normalize_admin_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not EMAIL_RE.match(v):
            raise ValueError("INVALID_ADMIN_EMAIL")
        return v


class AcademicBaselineIn(BaseModel):
    model_config = ConfigDict(extra="ignore")

    current_session: str = Field(min_length=1, max_length=20)
    academic_start_month: Literal["april", "june", "july"]
    academic_end_month: Literal["march", "may"]
    working_days_per_week: Literal[5, 6]
    class_levels_enabled: list[str] = Field(min_length=1)


class ModulesLimitsIn(BaseModel):
    model_config = ConfigDict(extra="ignore")

    modules: dict[str, bool]
    limits: dict[str, int]
    features: dict[str, bool]


class PlanInfoIn(BaseModel):
    model_config = ConfigDict(extra="ignore")

    plan_type: Literal["pilot", "starter", "standard", "premium"] = "pilot"
    is_test: bool = False
    trial_days: int = Field(default=0, ge=0, le=365)
    billing_start_date: date | None = None


class SuperadminSchoolCreateIn(BaseModel):
    model_config = ConfigDict(extra="ignore")

    school_identity: SchoolIdentityIn
    location_contact: LocationContactIn
    management_admin: ManagementAdminIn
    academic_baseline: AcademicBaselineIn
    modules_limits: ModulesLimitsIn
    plan_info: PlanInfoIn


class SuperadminSchoolCreateOut(BaseModel):
    success: bool
    data: dict[str, Any]
