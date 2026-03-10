from typing import Optional

from pydantic import BaseModel, ConfigDict


class SectionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    class_id: int
    name: str


class SectionOut(BaseModel):
    id: int
    public_id: str
    school_id: int
    class_id: int
    name: str
    class_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
