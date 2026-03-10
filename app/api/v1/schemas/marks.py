from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MarksRecordIn(BaseModel):
    student_id: int
    subject_id: int
    exam_type: str
    marks_obtained: int
    max_marks: int
    model_config = ConfigDict(extra="forbid")


class MarksSubmissionIn(BaseModel):
    section_id: int
    subject_id: int
    exam_type: str
    model_config = ConfigDict(extra="forbid")


class MarksRecordOut(BaseModel):
    id: int
    school_id: int
    student_id: int
    subject_id: int
    exam_type: str
    marks_obtained: int
    max_marks: int
    recorded_by_user_id: int | None
    student_name: str | None = None
    roll_no: str | None = None
    class_name: str | None = None
    section_name: str | None = None
    subject_name: str | None = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class MarksSubmissionOut(BaseModel):
    id: int
    school_id: int
    section_id: int
    subject_id: int
    exam_type: str
    submitted_by_user_id: int | None
    status: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
