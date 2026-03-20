from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.phone import normalize_phone

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PIN_RE = re.compile(r"^\d{6}$")


class Phase1OnboardingIn(BaseModel):
    model_config = ConfigDict(extra="ignore")

    school_name: str = Field(min_length=3, max_length=255)
    school_code: str = Field(min_length=2, max_length=64)
    board: str = Field(min_length=1, max_length=64)
    category: str = Field(min_length=1, max_length=64)
    medium: str = Field(min_length=1, max_length=64)
    school_type: str = Field(min_length=1, max_length=64)
    established_year: int = Field(ge=1800)
    affiliation_number: str | None = Field(default=None, max_length=64)
    udise_code: str | None = Field(default=None, max_length=32)

    street: str | None = Field(default=None, max_length=255)
    area: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=128)
    district: str | None = Field(default=None, max_length=128)
    state: str | None = Field(default=None, max_length=128)
    pin_code: str = Field(min_length=6, max_length=6)
    country: str | None = Field(default=None, max_length=128)
    landmark: str | None = Field(default=None, max_length=255)
    school_phone: str = Field(min_length=10, max_length=20)
    school_email: str = Field(min_length=5, max_length=255)
    website: str | None = Field(default=None, max_length=255)

    admin_first_name: str = Field(min_length=1, max_length=100)
    admin_last_name: str = Field(min_length=1, max_length=100)
    admin_designation: str | None = Field(default=None, max_length=100)
    admin_department: str | None = Field(default=None, max_length=100)
    admin_employee_id: str | None = Field(default=None, max_length=64)
    admin_phone: str = Field(min_length=10, max_length=20)
    admin_email: str = Field(min_length=5, max_length=255)
    language_preference: str | None = Field(default=None, max_length=32)
    timezone: str | None = Field(default=None, max_length=64)

    current_session: str = Field(min_length=1, max_length=64)
    academic_start_month: int = Field(ge=1, le=12)
    academic_end_month: int = Field(ge=1, le=12)
    working_days_per_week: int = Field(ge=1, le=7)
    class_levels: list[str] = Field(min_length=1)
    lkg_available: bool = False
    ukg_available: bool = False
    pre_nursery_available: bool = False

    modules_enabled: list[str] = Field(min_length=1)
    max_students: int = Field(gt=0)
    max_teachers: int = Field(gt=0)
    max_staff: int = Field(gt=0)
    storage_limit_gb: int = Field(gt=0)
    api_access: bool = False
    bulk_operations: bool = False
    custom_reports: bool = False

    @field_validator(
        "school_name",
        "school_code",
        "board",
        "category",
        "medium",
        "school_type",
        "current_session",
        mode="before",
    )
    @classmethod
    def strip_required(cls, value: str) -> str:
        return value.strip()

    @field_validator("school_code", mode="after")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator(
        "affiliation_number",
        "udise_code",
        "street",
        "area",
        "city",
        "district",
        "state",
        "country",
        "landmark",
        "website",
        "admin_designation",
        "admin_department",
        "admin_employee_id",
        "language_preference",
        "timezone",
        mode="before",
    )
    @classmethod
    def normalize_optional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @field_validator("school_email", "admin_email", mode="before")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        value = value.strip().lower()
        if not EMAIL_RE.match(value):
            raise ValueError("INVALID_EMAIL")
        return value

    @field_validator("school_phone", "admin_phone", mode="before")
    @classmethod
    def normalize_phone_field(cls, value: str) -> str:
        normalized = normalize_phone(value)
        if len(normalized) != 10:
            raise ValueError("INVALID_PHONE")
        return normalized

    @field_validator("pin_code")
    @classmethod
    def validate_pin(cls, value: str) -> str:
        if not PIN_RE.match(value):
            raise ValueError("INVALID_PIN_CODE")
        return value

    @field_validator("class_levels", "modules_enabled")
    @classmethod
    def validate_non_empty_list(cls, value: list[str], info) -> list[str]:
        cleaned = [item.strip() for item in value if item and item.strip()]
        if not cleaned:
            if info.field_name == "class_levels":
                raise ValueError("INVALID_CLASS_LEVELS")
            if info.field_name == "modules_enabled":
                raise ValueError("INVALID_MODULES_ENABLED")
            raise ValueError("INVALID_LIST")
        return cleaned

    @model_validator(mode="after")
    def validate_established_year(self) -> "Phase1OnboardingIn":
        current_year = datetime.now().year
        if self.established_year > current_year:
            raise ValueError("INVALID_ESTABLISHED_YEAR")
        return self


class Phase1ValidateIn(BaseModel):
    model_config = ConfigDict(extra="ignore")

    school_code: str | None = None
    udise_code: str | None = None
    school_email: str | None = None
    admin_phone: str | None = None
    admin_email: str | None = None

    @field_validator("school_code", mode="before")
    @classmethod
    def normalize_code(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().upper()

    @field_validator("school_email", "admin_email", mode="before")
    @classmethod
    def normalize_email(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip().lower()
        if not EMAIL_RE.match(value):
            raise ValueError("INVALID_EMAIL")
        return value

    @field_validator("admin_phone", mode="before")
    @classmethod
    def normalize_phone_field(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = normalize_phone(value)
        if len(normalized) != 10:
            raise ValueError("INVALID_PHONE")
        return normalized


class Phase1DraftIn(BaseModel):
    model_config = ConfigDict(extra="ignore")

    payload: dict[str, Any]


class Phase1DraftOut(BaseModel):
    id: str
    payload: dict[str, Any]
    status: str
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Phase1OnboardingOut(BaseModel):
    school: dict[str, Any]
    management_admin: dict[str, Any]
    onboarding: dict[str, Any]


class Phase1ValidateOut(BaseModel):
    valid: bool
    conflicts: list[str] = Field(default_factory=list)

