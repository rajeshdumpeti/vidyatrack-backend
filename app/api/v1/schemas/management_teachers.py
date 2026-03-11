from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.phone import normalize_phone

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class ManagementCreateTeacherIn(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str = Field(min_length=1, max_length=200)
    email: str | None = Field(default=None, min_length=5, max_length=255)
    phone: str | None = Field(default=None, min_length=10, max_length=20)
    section_id: int
    school_id: int

    @model_validator(mode="after")
    def validate_contact(self) -> "ManagementCreateTeacherIn":
        if not self.email and not self.phone:
            raise ValueError("email_or_phone_required")
        if self.email:
            self.email = self.email.strip()
            if not EMAIL_RE.match(self.email):
                raise ValueError("invalid_email_format")
        if self.phone:
            self.phone = normalize_phone(self.phone)
        return self


class ManagementCreateTeacherOut(BaseModel):
    user_id: int
    teacher_id: int
    teacher_public_id: str
    name: str
    email: str | None = None
    phone: str | None = None
    section_id: int
    model_config = ConfigDict(from_attributes=True)
