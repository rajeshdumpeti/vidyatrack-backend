from pydantic import BaseModel, ConfigDict


class TeachingAssignmentCreate(BaseModel):
    section_id: int
    subject_id: int
    teacher_id: int
    school_id: int


class TeachingAssignmentOut(BaseModel):
    id: int
    school_id: int
    section_id: int
    subject_id: int
    teacher_id: int

    model_config = ConfigDict(from_attributes=True)
