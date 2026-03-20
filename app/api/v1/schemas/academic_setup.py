from pydantic import BaseModel


class AcademicClassOut(BaseModel):
    id: int
    name: str


class AcademicSectionOut(BaseModel):
    id: int
    name: str
    class_id: int
    class_name: str | None = None


class AcademicSubjectOut(BaseModel):
    id: int
    name: str


class AcademicSetupOut(BaseModel):
    school_id: int
    classes: list[AcademicClassOut]
    sections: list[AcademicSectionOut]
    subjects: list[AcademicSubjectOut]
