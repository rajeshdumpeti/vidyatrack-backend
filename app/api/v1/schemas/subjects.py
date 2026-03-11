from pydantic import BaseModel, ConfigDict


class SubjectCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    school_id: int


class SubjectOut(BaseModel):
    id: int
    public_id: str
    school_id: int
    name: str

    model_config = ConfigDict(from_attributes=True)
