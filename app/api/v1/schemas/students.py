from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StudentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    date_of_birth: date | None = None
    gender: str | None = None
    status: Literal["DRAFT", "ACTIVE"] = "ACTIVE"
    academic_year: str | None = None
    section_id: int | None = None
    roll_number: str | None = Field(default=None, min_length=1, max_length=32)
    admission_date: date | None = None
    admission_number: str | None = Field(default=None, min_length=1, max_length=64)
    blood_group: str | None = None
    nationality: str | None = None
    religion: str | None = None
    caste_category: str | None = None
    mother_tongue: str | None = None
    aadhaar_number: str | None = None
    birth_cert_number: str | None = None
    previous_school_name: str | None = None
    previous_school_tc_number: str | None = None
    address: str | None = None
    parent_phone: str
    parent_name: str | None = None
    emergency_contact_name: str | None = None
    emergency_contact_relation: str | None = None
    emergency_contact_phone: str | None = None

    @model_validator(mode="after")
    def validate_name(self) -> "StudentCreate":
        if (self.name is None or self.name.strip() == "") and not (
            self.first_name and self.last_name
        ):
            raise ValueError("name_or_first_last_required")
        if self.name is not None:
            self.name = self.name.strip()
        if self.first_name is not None:
            self.first_name = self.first_name.strip()
        if self.last_name is not None:
            self.last_name = self.last_name.strip()
        return self


class StudentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    date_of_birth: date | None = None
    gender: str | None = None
    status: Literal["DRAFT", "ACTIVE"] | None = None
    academic_year: str | None = None
    section_id: int | None = None
    roll_number: str | None = Field(default=None, min_length=1, max_length=32)
    admission_date: date | None = None
    admission_number: str | None = Field(default=None, min_length=1, max_length=64)
    blood_group: str | None = None
    nationality: str | None = None
    religion: str | None = None
    caste_category: str | None = None
    mother_tongue: str | None = None
    aadhaar_number: str | None = None
    birth_cert_number: str | None = None
    previous_school_name: str | None = None
    previous_school_tc_number: str | None = None
    address: str | None = None
    parent_phone: str | None = None
    parent_name: str | None = None
    emergency_contact_name: str | None = None
    emergency_contact_relation: str | None = None
    emergency_contact_phone: str | None = None


class StudentOut(BaseModel):
    id: int
    public_id: str
    school_id: int
    student_code: str | None = None
    name: str
    first_name: str | None = None
    last_name: str | None = None
    date_of_birth: date | None = None
    gender: str | None = None
    section_id: int | None = None
    section_name: str | None = None
    class_id: int | None = None
    class_name: str | None = None
    roll_number: str | None = None
    admission_date: date | None = None
    academic_year: str | None = None
    parent_phone: str
    parent_name: str | None = None
    status: str | None = None

    model_config = ConfigDict(from_attributes=True)


class StudentPersonalDetails(BaseModel):
    date_of_birth: str | None = None
    gender: str | None = None
    blood_group: str | None = None
    nationality: str | None = None
    religion: str | None = None
    caste_category: str | None = None
    mother_tongue: str | None = None
    aadhaar_number: str | None = None
    birth_cert_number: str | None = None
    address: str | None = None


class StudentGuardianOut(BaseModel):
    name: str | None = None
    relation: str | None = None
    phone: str | None = None


class StudentAttendanceSummary(BaseModel):
    percentage: float
    present_days: int
    absent_days: int
    total_days: int


class StudentRecentResult(BaseModel):
    subject_name: str
    exam_type: str
    marks_obtained: int
    max_marks: int


class StudentProfileOut(BaseModel):
    id: int
    public_id: str
    student_code: str
    name: str
    class_id: int | None
    class_name: str | None
    section_id: int | None
    section_name: str | None
    status: str
    academic_year: str | None = None
    admission_number: str | None = None
    previous_school_name: str | None = None
    previous_school_tc_number: str | None = None
    personal_details: StudentPersonalDetails
    guardians: list[StudentGuardianOut]
    attendance: StudentAttendanceSummary
    recent_results: list[StudentRecentResult]


class StudentReportCardRow(BaseModel):
    subject_name: str
    exam_type: str
    marks_obtained: int
    max_marks: int
    percentage: float
    grade: str


class StudentReportCardOut(BaseModel):
    student_id: int
    student_name: str
    student_code: str
    public_id: str
    class_name: str | None
    section_name: str | None
    school_name: str | None = None
    school_address: str | None = None
    academic_year: str | None = None
    attendance_percentage: float
    present_days: int
    absent_days: int
    total_days: int
    total_obtained: int
    total_max: int
    overall_percentage: float
    overall_grade: str
    generated_at: str
    rows: list[StudentReportCardRow]


class StudentImportRowOut(BaseModel):
    row_number: int
    status: Literal["valid", "invalid", "duplicate"]
    errors: list[str] = Field(default_factory=list)
    student_name: str | None = None
    parent_phone: str | None = None
    class_name: str | None = None
    section_name: str | None = None
    roll_number: str | None = None


class StudentImportPreviewOut(BaseModel):
    import_token: str | None = None
    total_rows: int
    valid_rows: int
    invalid_rows: int
    duplicate_rows: int
    rows: list[StudentImportRowOut]


class StudentImportCommitIn(BaseModel):
    import_token: str
    mode: Literal["skip_duplicates"] = "skip_duplicates"


class StudentImportCommitOut(BaseModel):
    total_rows: int
    created_rows: int
    duplicate_rows: int
    failed_rows: int
    errors: list[StudentImportRowOut] = Field(default_factory=list)
