from pydantic import BaseModel


class TeacherMeOut(BaseModel):
    teacher_id: int
    school_id: int
    name: str
    email: str | None = None
    phone: str | None = None


class TeachingAssignmentOut(BaseModel):
    school_id: int
    section_id: int
    section_name: str
    class_id: int
    class_name: str
    subject_id: int
    subject_name: str


class TeacherAttendanceSectionOut(BaseModel):
    school_id: int
    section_id: int
    section_name: str
    class_id: int
    class_name: str


class TeacherContextSubjectOut(BaseModel):
    subject_id: int
    subject_name: str


class TeacherContextOut(BaseModel):
    teacher_id: int
    user_id: int
    school_id: int
    school_name: str
    class_id: int | None = None
    class_name: str | None = None
    section_id: int | None = None
    section_name: str | None = None
    subjects: list[TeacherContextSubjectOut]


class TeacherReadinessOut(BaseModel):
    status: str
    school_id: int | None = None
    teacher_id: int | None = None
    section_id: int | None = None
    checks: dict[str, bool]
    missing_requirements: list[str]
    recommended_next_action: str | None = None
