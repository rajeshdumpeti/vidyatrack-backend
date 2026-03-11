from pydantic import BaseModel, ConfigDict


class ClassCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str


class ClassOut(BaseModel):
    id: int
    public_id: str
    school_id: int
    name: str

    model_config = ConfigDict(from_attributes=True)
