from pydantic import BaseModel


class TeacherAttendanceSectionOut(BaseModel):
    section_id: int
    section_name: str
    class_id: int
    class_name: str
