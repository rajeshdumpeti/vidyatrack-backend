from pydantic import BaseModel, ConfigDict


class OutboxRunOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    processed: int
